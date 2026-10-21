# Выкладка Voxgram в TestFlight

Сборку подписывает и загружает в TestFlight workflow `.github/workflows/testflight.yml`.
Профили (provisioning profiles) для приложения и расширений он создаёт сам через App Store Connect API —
вручную их делать не нужно. Один раз нужно подготовить сертификат, ключ API, группу приложений и секреты.

## 1. Ключ App Store Connect API

1. https://appstoreconnect.apple.com → **Users and Access** → **Integrations** → **App Store Connect API**.
2. **Team Keys** → **+** (Generate API Key), имя `GitHub CI`, доступ **Admin**
   (нужен, чтобы создавать идентификаторы и профили).
3. Скачай файл `AuthKey_XXXXXXXXXX.p8` — скачать его можно только один раз.
4. Запиши **Key ID** (в списке ключей) и **Issuer ID** (над списком).

## 2. Сертификат Apple Distribution (без Mac)

Команды для OpenSSL (на Windows — в Git Bash):

```bash
openssl genrsa -out distribution.key 2048
openssl req -new -key distribution.key -out distribution.csr -subj "/CN=Voxgram Distribution/C=RU"
```

1. https://developer.apple.com/account/resources/certificates/list → **+** → **Apple Distribution** →
   загрузи `distribution.csr` → скачай `distribution.cer`.
2. Собери `.p12` (придумай пароль):

```bash
openssl x509 -inform DER -in distribution.cer -out distribution.pem
openssl pkcs12 -export -inkey distribution.key -in distribution.pem -out distribution.p12 \
  -keypbe PBE-SHA1-3DES -certpbe PBE-SHA1-3DES -macalg sha1 -password pass:ПАРОЛЬ
base64 -w0 distribution.p12 > distribution.p12.base64.txt
```

Файлы `distribution.key` и `distribution.p12` храни в надёжном месте и никому не отправляй.

## 3. Группа приложений

https://developer.apple.com/account/resources/identifiers/list/applicationGroup → **+** → **App Groups** →
описание `Voxgram`, идентификатор `group.com.voxgram.app`.

## 4. Секреты GitHub

Репозиторий → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Секрет | Что вставить |
|---|---|
| `APPLE_TEAM_ID` | Team ID из https://developer.apple.com/account → Membership details |
| `IOS_DIST_CERT_P12_BASE64` | содержимое `distribution.p12.base64.txt` |
| `IOS_DIST_CERT_PASSWORD` | пароль от `.p12` |
| `ASC_KEY_ID` | Key ID из шага 1 |
| `ASC_ISSUER_ID` | Issuer ID из шага 1 |
| `ASC_PRIVATE_KEY` | весь текст файла `AuthKey_XXXXXXXXXX.p8`, включая строки `-----BEGIN/END PRIVATE KEY-----` |

## 5. Первый запуск и привязка группы

1. **Actions** → **TestFlight** → **Run workflow** (ветка `layer-224`).
2. Workflow создаст идентификаторы `com.voxgram.app` и расширений (`.Share`, `.NotificationService`,
   `.NotificationContent`, `.SiriIntents`, `.Widget`, `.BroadcastUpload`) с App Groups и Push Notifications.
   Привязать к ним саму группу через API нельзя, поэтому первый запуск остановится с сообщением, для каких
   идентификаторов её не хватает.
3. https://developer.apple.com/account/resources/identifiers/list → для каждого из 7 идентификаторов:
   открыть → **App Groups** → **Configure** → отметить `group.com.voxgram.app` → **Continue** → **Save**.
4. Запусти workflow ещё раз.

## 6. Приложение в App Store Connect

https://appstoreconnect.apple.com → **Apps** → **+** → **New App**: платформа iOS, имя `Voxgram`,
язык, Bundle ID `com.voxgram.app` (появится после первого запуска workflow), SKU `voxgram`.
Сделай это до загрузки сборки, иначе загрузка завершится ошибкой.

## 7. TestFlight

После загрузки сборка обрабатывается в App Store Connect 10–30 минут (**TestFlight** → **iOS Builds**).
Вопроса про шифрование не будет: в приложении стоит `ITSAppUsesNonExemptEncryption = NO`.

- **Internal Testing** — до 100 человек из команды App Store Connect, без проверки Apple.
- **External Testing** — по ссылке или email, первую сборку версии проверяет Apple (Beta App Review, обычно до суток).

## Номер сборки

По умолчанию номер сборки — число коммитов + `build_number_offset`. Повторно загрузить тот же номер нельзя:
чтобы перезалить тот же коммит, укажи при запуске workflow поле **Build number** больше последнего загруженного.
