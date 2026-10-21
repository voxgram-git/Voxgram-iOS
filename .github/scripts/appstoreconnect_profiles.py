#!/usr/bin/env python3
"""Prepare App Store provisioning profiles for the app and its extensions via the App Store Connect API.

For every bundle identifier the script makes sure the identifier exists and has the capabilities the build needs,
then (re)creates an App Store profile that contains the distribution certificate from the given .p12 and writes it
to the output directory. App group membership can't be assigned through the API, so the script fails with
instructions if a profile comes back without the app group.
"""

import argparse
import base64
import json
import os
import plistlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

import jwt

API = 'https://api.appstoreconnect.apple.com/v1'

# Bundle id suffix -> human readable name; matches the extensions Telegram/BUILD embeds in the app
TARGETS = {
    '': 'App',
    '.Share': 'Share Extension',
    '.NotificationService': 'Notification Service Extension',
    '.NotificationContent': 'Notification Content Extension',
    '.SiriIntents': 'Intents Extension',
    '.Widget': 'Widget Extension',
    '.BroadcastUpload': 'Broadcast Upload Extension',
}

PROFILE_PREFIX = 'Voxgram CI'


class Client:
    def __init__(self, key_id, issuer_id, private_key):
        self.key_id = key_id
        self.issuer_id = issuer_id
        self.private_key = private_key
        self.token = None
        self.token_expiry = 0

    def _auth(self):
        now = int(time.time())
        if self.token is None or now > self.token_expiry - 60:
            self.token_expiry = now + 15 * 60
            self.token = jwt.encode(
                {'iss': self.issuer_id, 'iat': now, 'exp': self.token_expiry, 'aud': 'appstoreconnect-v1'},
                self.private_key,
                algorithm='ES256',
                headers={'kid': self.key_id, 'typ': 'JWT'},
            )
        return self.token

    def request(self, method, path, body=None):
        url = path if path.startswith('https://') else API + path
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header('Authorization', 'Bearer ' + self._auth())
        if data is not None:
            req.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            details = e.read().decode(errors='replace')
            raise SystemExit(f'App Store Connect API {method} {path} failed with {e.code}: {details}')

    def get_all(self, path):
        items = []
        while path:
            resp = self.request('GET', path)
            items.extend(resp['data'])
            path = resp.get('links', {}).get('next')
        return items


def certificate_serial(p12_path, password):
    pem = subprocess.run(
        ['openssl', 'pkcs12', '-in', p12_path, '-nokeys', '-passin', 'pass:' + password],
        capture_output=True, check=False,
    )
    if pem.returncode != 0:
        # OpenSSL 3 needs -legacy for p12 files exported by Keychain Access
        pem = subprocess.run(
            ['openssl', 'pkcs12', '-legacy', '-in', p12_path, '-nokeys', '-passin', 'pass:' + password],
            capture_output=True, check=True,
        )
    out = subprocess.run(['openssl', 'x509', '-noout', '-serial'], input=pem.stdout, capture_output=True, check=True)
    serial = out.stdout.decode().strip().split('=', 1)[1]
    return serial.upper().lstrip('0')


def ensure_bundle_id(client, identifier, name):
    for item in client.get_all(f'/bundleIds?filter[identifier]={identifier}&limit=200'):
        if item['attributes']['identifier'] == identifier:
            return item
    print(f'Creating bundle id {identifier}')
    resp = client.request('POST', '/bundleIds', {
        'data': {'type': 'bundleIds', 'attributes': {'identifier': identifier, 'name': name, 'platform': 'IOS'}}
    })
    return resp['data']


def ensure_capability(client, bundle_id, capability):
    existing = client.get_all(f'/bundleIds/{bundle_id["id"]}/bundleIdCapabilities?limit=200')
    if any(c['attributes']['capabilityType'] == capability for c in existing):
        return
    print(f'Enabling {capability} for {bundle_id["attributes"]["identifier"]}')
    client.request('POST', '/bundleIdCapabilities', {
        'data': {
            'type': 'bundleIdCapabilities',
            'attributes': {'capabilityType': capability},
            'relationships': {'bundleId': {'data': {'type': 'bundleIds', 'id': bundle_id['id']}}},
        }
    })


def profile_entitlements(content_b64):
    der = base64.b64decode(content_b64)
    out = subprocess.run(['openssl', 'smime', '-inform', 'der', '-verify', '-noverify'], input=der,
                         capture_output=True, check=True)
    return plistlib.loads(out.stdout)['Entitlements']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle-id', required=True)
    parser.add_argument('--key-id', required=True)
    parser.add_argument('--issuer-id', required=True)
    parser.add_argument('--private-key-path', required=True)
    parser.add_argument('--p12-path', required=True)
    parser.add_argument('--p12-password-env', default='IOS_DIST_CERT_PASSWORD')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    with open(args.private_key_path) as f:
        client = Client(args.key_id, args.issuer_id, f.read())

    serial = certificate_serial(args.p12_path, os.environ.get(args.p12_password_env, ''))
    certificates = client.get_all('/certificates?limit=200')
    certificate = next((c for c in certificates
                        if c['attributes'].get('serialNumber', '').upper().lstrip('0') == serial
                        and c['attributes'].get('certificateType') in ('DISTRIBUTION', 'IOS_DISTRIBUTION')), None)
    if certificate is None:
        raise SystemExit(f'The distribution certificate from the .p12 (serial {serial}) was not found in the Apple '
                         f'Developer account. Export the Apple Distribution certificate of this team.')

    os.makedirs(args.output, exist_ok=True)
    app_group = f'group.{args.bundle_id}'
    missing_group = []
    for suffix, name in TARGETS.items():
        identifier = args.bundle_id + suffix
        bundle_id = ensure_bundle_id(client, identifier, f'Voxgram {name}')
        ensure_capability(client, bundle_id, 'APP_GROUPS')
        if suffix == '':
            ensure_capability(client, bundle_id, 'PUSH_NOTIFICATIONS')

        profile_name = f'{PROFILE_PREFIX} {identifier}'
        for profile in client.get_all(f'/bundleIds/{bundle_id["id"]}/profiles?limit=200'):
            if profile['attributes']['name'] == profile_name:
                client.request('DELETE', f'/profiles/{profile["id"]}')
        resp = client.request('POST', '/profiles', {
            'data': {
                'type': 'profiles',
                'attributes': {'name': profile_name, 'profileType': 'IOS_APP_STORE'},
                'relationships': {
                    'bundleId': {'data': {'type': 'bundleIds', 'id': bundle_id['id']}},
                    'certificates': {'data': [{'type': 'certificates', 'id': certificate['id']}]},
                },
            }
        })
        content = resp['data']['attributes']['profileContent']
        entitlements = profile_entitlements(content)
        if app_group not in entitlements.get('com.apple.security.application-groups', []):
            missing_group.append(identifier)
        if suffix == '' and 'aps-environment' not in entitlements:
            raise SystemExit(f'The profile for {identifier} has no push notification entitlement')
        path = os.path.join(args.output, f'{identifier}.mobileprovision')
        with open(path, 'wb') as f:
            f.write(base64.b64decode(content))
        print(f'Wrote {path}')

    if missing_group:
        raise SystemExit(
            f'App group {app_group} is not assigned to: {", ".join(missing_group)}.\n'
            f'In developer.apple.com -> Certificates, Identifiers & Profiles: create the App Group "{app_group}" '
            f'(Identifiers -> App Groups) and, for each identifier above, open it, click "Configure" next to '
            f'App Groups, tick {app_group} and save. Then run the workflow again.')


if __name__ == '__main__':
    sys.exit(main())
