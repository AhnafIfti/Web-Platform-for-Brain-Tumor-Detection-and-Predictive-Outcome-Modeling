# Interface and security update

The active application is in `D:\Taha work\Neuro Vision AI`. Launch using the existing desktop BAT shortcut. Frontend: http://127.0.0.1:9130/; backend: port 9131.

## Enable two-factor authentication

1. Sign in and open Settings > Two-factor authentication.
2. Enter the current account password and choose Set up authenticator.
3. Scan the QR code with a TOTP authenticator app (or enter the manual key).
4. Enter the password and current six-digit code to confirm.
5. Save the eight recovery codes privately. They are shown once; each can be used once.

Enrollment is per account and requires the account holder's authenticator. Existing accounts are not automatically enrolled. Once enabled, every new login requires the second factor, including admin access. Existing unverified sessions must sign in again. Challenges expire after five minutes; setup expires after ten. Reused authenticator codes are rejected and failed code attempts trigger increasing delays. Disabling requires the password plus an authenticator or recovery code. Recovery codes are stored as password hashes. Protect the database and backups because authenticator secrets must remain available to validate codes. If all factors are lost, an authorized server administrator must verify the user's identity before resetting enrollment; there is no public bypass.

## Demo flow

Open a completed analysis. Original FLAIR and the segmentation overlay appear side by side on square 224 x 224 model-grid views. The slice slider changes both views together. Zoom buttons zoom both; drag either image to pan both. Fit returns to 100%. Full screen expands the paired viewer; Exit full screen or Escape restores it. Overlay/mask selection affects the right image; the original stays visible on the left.

Download analysis summary saves a PDF with the representative slice and recorded inference statistics. It does not export the current viewer zoom or a new prediction. Open summary retains the PDF preview. The download fetches an authenticated JSON envelope containing the generated PDF, then saves a PDF Blob locally; this avoids the interrupted attachment response observed in this machine's browser. Ownership checks and no-store headers apply to both export formats.

The interface uses a light palette, larger typography, simplified dashboard and locally built Tailwind CSS. Model architecture, checkpoint, preprocessing, inference and historical metrics are unchanged.

## Validation

Run `.venv\Scripts\python.exe manage.py test --settings=config.test_settings --noinput`. Include the isolated Chrome browser test with `RUN_BROWSER_TESTS=1`. Browser test data stays in the temporary test database/media, never the real analysis collection. Build CSS with `npm run build:css`; publish static assets with `.venv\Scripts\python.exe manage.py collectstatic --noinput`.
