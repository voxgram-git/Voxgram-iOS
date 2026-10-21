# Выкладка Voxgram в TestFlight

Сборку подписывает и загружает в TestFlight workflow `.github/workflows/testflight.yml`
(Actions → **TestFlight** → **Run workflow**). Есть два способа настройки:

- **Через владельца аккаунта** (ниже) — владелец один раз делает сертификат и профили, у разработчика доступ
  только к приложению Voxgram. Подробно для владельца: [testflight-owner.md](testflight-owner.md).
- **Через ключ API** — если есть свой аккаунт Apple Developer или командный ключ App Store Connect API;
  профили workflow создаёт сам (раздел в конце).

## Способ 1: через владельца аккаунта

### 1. Запрос на сертификат

На Windows: установи Git for Windows, в пустой папке → правой кнопкой → **Open Git Bash here**:

```bash
openssl genrsa -out distribution.key 2048
MSYS_NO_PATHCONV=1 openssl req -new -key distribution.key -out distribution.csr \
  -subj "/emailAddress=твоя@почта.com/CN=Voxgram Distribution/C=RU"
```

Отправь владельцу `distribution.csr`. Файл `distribution.key` никому не отправляй.

### 2. Что пришлёт владелец

- `distribution.cer`
- zip с 7 файлами `.mobileprovision`
- Team ID
- приглашение в App Store Connect (роль App Manager, только Voxgram) — прими его

### 3. Файл .p12

```bash
openssl x509 -inform DER -in distribution.cer -out distribution.pem
openssl pkcs12 -export -inkey distribution.key -in distribution.pem -out distribution.p12 \
  -keypbe PBE-SHA1-3DES -certpbe PBE-SHA1-3DES -macalg sha1 -passout pass:ПАРОЛЬ
base64 -w0 distribution.p12 > distribution.p12.base64.txt
base64 -w0 profiles.zip > profiles.zip.base64.txt
```

(`profiles.zip` — архив с профилями от владельца, положи его в ту же папку.)

### 4. Пароль приложения для Apple ID

https://account.apple.com → **Sign-In and Security** → **App-Specific Passwords** → **+** → имя `GitHub` →
скопируй пароль вида `abcd-efgh-ijkl-mnop`.

### 5. Секреты GitHub

Репозиторий → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Секрет | Что вставить |
|---|---|
| `APPLE_TEAM_ID` | Team ID от владельца |
| `IOS_DIST_CERT_P12_BASE64` | содержимое `distribution.p12.base64.txt` |
| `IOS_DIST_CERT_PASSWORD` | пароль от `.p12` |
| `IOS_PROFILES_ZIP_BASE64` | содержимое `profiles.zip.base64.txt` |
| `APPLE_ID` | твой Apple ID (email), которому владелец дал доступ |
| `APPLE_APP_PASSWORD` | пароль приложения из шага 4 |
| `ASC_PROVIDER` | нужен, только если твой Apple ID состоит в нескольких командах — см. ниже |

### 6. Запуск

Actions → **TestFlight** → **Run workflow** (ветка `layer-224`).

Workflow сначала проверит профили и напишет, чего не хватает (нет профиля, нет App Group или push,
не тот сертификат или команда). Если твой Apple ID состоит в нескольких командах и загрузка просит
указать провайдера, найди в логе шага **Upload to TestFlight** таблицу `--list-providers` и добавь секрет
`ASC_PROVIDER` со значением из колонки **ProviderShortName** для команды владельца.

## TestFlight

После загрузки сборка обрабатывается в App Store Connect 10–30 минут (**TestFlight** → **iOS Builds**).
Вопроса про шифрование не будет: в приложении стоит `ITSAppUsesNonExemptEncryption = NO`.

- **Internal Testing** — до 100 человек из команды App Store Connect, без проверки Apple.
- **External Testing** — по ссылке или email; первую сборку версии проверяет Apple (Beta App Review, обычно до суток).

## Номер сборки

По умолчанию номер сборки — число коммитов + `build_number_offset`. Повторно загрузить тот же номер нельзя:
чтобы перезалить тот же коммит, укажи при запуске поле **Build number** больше последнего загруженного.

## Способ 2: через ключ App Store Connect API

Подходит, если аккаунт свой или владелец даёт командный ключ (Team Key, роль Admin или App Manager).
Ключ действует на всю команду. Секрет `IOS_PROFILES_ZIP_BASE64` в этом случае не задавай — по нему workflow
выбирает способ 1.

1. App Store Connect → **Users and Access** → **Integrations** → **App Store Connect API** → **Team Keys** →
   **+**. Скачай `AuthKey_XXXXXXXXXX.p8` (скачать можно один раз), запиши **Key ID** и **Issuer ID**.
2. Сертификат Apple Distribution и `.p12` — как в шагах 1 и 3 способа 1 (сертификат выпускается по `.csr` в
   Certificates → **+** → Apple Distribution).
3. Создай App Group `group.com.voxgram.app` (Identifiers → **+** → App Groups).
4. Секреты: `APPLE_TEAM_ID`, `IOS_DIST_CERT_P12_BASE64`, `IOS_DIST_CERT_PASSWORD`, `ASC_KEY_ID`,
   `ASC_ISSUER_ID`, `ASC_PRIVATE_KEY` (весь текст `.p8`, вместе со строками `-----BEGIN/END PRIVATE KEY-----`).
5. Запусти workflow. Он создаст 7 идентификаторов с App Groups и Push и остановится: привязать группу через API
   нельзя. Открой каждый идентификатор `com.voxgram.app*` → App Groups → **Configure** → отметь
   `group.com.voxgram.app` → Save. Запусти ещё раз — профили создадутся сами.
6. Создай приложение в App Store Connect (Apps → **+** → New App, Bundle ID `com.voxgram.app`) до загрузки сборки.
