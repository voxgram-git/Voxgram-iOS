# Voxgram: что сделать владельцу аккаунта Apple Developer

Нужно один раз выпустить сертификат и профили для приложения Voxgram и дать разработчику доступ только к этому
приложению. Доступа к остальным приложениям, сертификатам и профилям команды он не получит.

Сайты:
- Certificates, Identifiers & Profiles: https://developer.apple.com/account/resources
- App Store Connect: https://appstoreconnect.apple.com

От разработчика понадобится файл **`distribution.csr`** (запрос на сертификат; приватный ключ остаётся у него).

## 1. Сертификат Apple Distribution

1. Certificates → **+**.
2. **Apple Distribution** → Continue.
3. **Choose File** → `distribution.csr` от разработчика → Continue.
4. **Download** → получится `distribution.cer`.

Отправь `distribution.cer` разработчику.

## 2. App Group

1. Identifiers → **+** → **App Groups** → Continue.
2. Description: `Voxgram`, Identifier: `group.com.voxgram.app` → Continue → Register.

## 3. Семь идентификаторов (App IDs)

Для каждой строки: Identifiers → **+** → **App IDs** → Continue → **App** → Continue, затем:
- Description — из таблицы;
- Bundle ID: **Explicit**, значение из таблицы;
- в Capabilities отметить **App Groups** (у первого ещё **Push Notifications**);
- Continue → Register.

| Description | Bundle ID (Explicit) | Capabilities |
|---|---|---|
| Voxgram | `com.voxgram.app` | App Groups, Push Notifications |
| Voxgram Share | `com.voxgram.app.Share` | App Groups |
| Voxgram Notification Service | `com.voxgram.app.NotificationService` | App Groups |
| Voxgram Notification Content | `com.voxgram.app.NotificationContent` | App Groups |
| Voxgram Intents | `com.voxgram.app.SiriIntents` | App Groups |
| Voxgram Widget | `com.voxgram.app.Widget` | App Groups |
| Voxgram Broadcast | `com.voxgram.app.BroadcastUpload` | App Groups |

Потом привяжи группу к каждому из 7 идентификаторов: открыть идентификатор → у **App Groups** нажать
**Configure** (или Edit) → отметить `group.com.voxgram.app` → Continue → **Save** → Confirm.

Push Notifications достаточно отметить; сертификат для push сейчас не нужен.

## 4. Семь профилей App Store

Для каждого из 7 идентификаторов:

1. Profiles → **+** → в разделе Distribution выбрать **App Store Connect** → Continue.
2. App ID: идентификатор из таблицы → Continue.
3. Certificate: сертификат из шага 1 (Apple Distribution, созданный сегодня) → Continue.
4. Name: `Voxgram AppStore` + конец идентификатора, например `Voxgram AppStore Share` → **Generate**.
5. **Download**.

Сложи 7 файлов `.mobileprovision` в один zip и отправь разработчику.

Профиль нужно делать **после** привязки App Group (шаг 3) — иначе группы в нём не будет и сборка не пройдёт.

## 5. Приложение в App Store Connect

Apps → **+** → **New App**:
- Platforms: iOS
- Name: `Voxgram`
- Primary Language: на выбор
- Bundle ID: `com.voxgram.app`
- SKU: `voxgram`
- User Access: **Limited Access**

## 6. Доступ для разработчика

Users and Access → **+**:
- имя и email разработчика (его Apple ID);
- Role: **App Manager**;
- **Access to Certificates, Identifiers & Profiles** — **не отмечать**;
- остальные дополнительные права — не отмечать;
- Apps: выбрать только **Voxgram**;
- Invite.

## 7. Team ID

Membership details на https://developer.apple.com/account → **Team ID** (10 символов) — отправь разработчику.

## Раз в год

Сертификат действует год, профили — до окончания сертификата. Когда срок подойдёт, разработчик пришлёт новый
`.csr`: повтори шаг 1 и пересоздай профили (шаг 4) с новым сертификатом.
Профили нужно пересоздать и если поменять Capabilities у любого из идентификаторов.
