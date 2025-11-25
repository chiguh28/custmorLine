# Render.com デプロイガイド

このドキュメントでは、LINE Bot アプリケーションをRender.comにデプロイする手順を説明します。

## 前提条件

- Gitリポジトリ(GitHub, GitLab, Bitbucket等)にコードがプッシュされていること
- Render.comアカウント(無料プランで可)
- LINE Developers Consoleでのチャネル設定が完了していること

## デプロイ手順

### 1. Gitリポジトリの準備

プロジェクトをGitリポジトリにプッシュします:

```bash
git add .
git commit -m "Add Render.com deployment configuration"
git push origin main
```

### 2. Render.comでBlueprintからデプロイ

1. [Render.com](https://render.com/)にログイン
2. ダッシュボードから **"New +"** → **"Blueprint"** を選択
3. GitリポジトリをRender.comに接続
4. リポジトリを選択し、`render.yaml`を検出させる
5. **"Apply"** をクリック

Render.comが自動的に以下を作成します:
- Webサービス(`custmorline-bot`)
- PostgreSQLデータベース(`custmorline-db`)

### 3. 環境変数の設定

Webサービスのダッシュボードで、以下の環境変数を設定します:

| 環境変数名 | 説明 | 取得方法 |
|-----------|------|---------|
| `LINE_CHANNEL_SECRET_CUSTOMER` | 客用BotのChannel Secret | LINE Developers Console > 客用チャネル > Basic settings |
| `LINE_CHANNEL_ACCESS_TOKEN_CUSTOMER` | 客用BotのChannel Access Token | LINE Developers Console > 客用チャネル > Messaging API |
| `LINE_CHANNEL_SECRET_THERAPIST` | セラピスト用BotのChannel Secret | LINE Developers Console > セラピスト用チャネル > Basic settings |
| `LINE_CHANNEL_ACCESS_TOKEN_THERAPIST` | セラピスト用BotのChannel Access Token | LINE Developers Console > セラピスト用チャネル > Messaging API |
| `LIFF_ID` | LIFF アプリのID | LINE Developers Console > LIFF > LIFF ID |
| `SALON_LOCATION` | サロンの住所 | 任意(デフォルト: プレサンス新栄リベラ1003) |

> [!NOTE]
> `DATABASE_URL`は自動的に設定されます(PostgreSQLデータベースとの接続)。

### 4. デプロイの確認

1. Render.comのダッシュボードで、デプロイが成功したことを確認
2. Webサービスの **URL** をコピー(例: `https://custmorline-bot.onrender.com`)

### 5. LINE Webhook URLの設定

#### 客用Bot
1. LINE Developers Console > 客用チャネル > Messaging API
2. **Webhook URL** に以下を設定:
   ```
   https://your-app-name.onrender.com/callback/customer
   ```
3. **Use webhook** を有効化
4. **Verify** ボタンで接続テスト

#### セラピスト用Bot
1. LINE Developers Console > セラピスト用チャネル > Messaging API
2. **Webhook URL** に以下を設定:
   ```
   https://your-app-name.onrender.com/callback/therapist
   ```
3. **Use webhook** を有効化
4. **Verify** ボタンで接続テスト

### 6. LIFF URLの更新

1. LINE Developers Console > LIFF
2. LIFF アプリの **Endpoint URL** を更新:
   ```
   https://your-app-name.onrender.com/booking
   ```

## デプロイ後の確認

### 動作確認

1. **客用Bot**:
   - LINE公式アカウントを友だち追加
   - リッチメニューから「料金表」「出勤表」をタップして画像が表示されることを確認
   - 「予約する」から予約画面が開くことを確認

2. **セラピスト用Bot**:
   - LINE公式アカウントを友だち追加
   - 「管理」から管理画面が開くことを確認
   - 出勤表画像をアップロードして配信されることを確認

### ログの確認

Render.comのダッシュボードで **Logs** タブを開き、エラーがないか確認します。

## トラブルシューティング

### デプロイが失敗する

- **ビルドエラー**: `requirements.txt`の依存関係を確認
- **起動エラー**: 環境変数が正しく設定されているか確認

### Webhookが動作しない

1. Render.comのログで接続を確認
2. LINE Developers ConsoleでWebhook URLを再確認
3. 環境変数(`LINE_CHANNEL_SECRET_*`)が正しいか確認

### データベース接続エラー

- `DATABASE_URL`が自動設定されているか確認
- PostgreSQLデータベースが正常に起動しているか確認

## 無料プランの制限

Render.comの無料プランには以下の制限があります:

- **Webサービス**: 15分間アクセスがないとスリープ状態になります
  - 初回アクセス時に起動に30秒程度かかる場合があります
- **PostgreSQL**: 90日間アクセスがないと削除されます
- **静的ファイル**: 再起動時にアップロードした画像は消えます
  - 出勤表画像は再アップロードが必要です

## 更新方法

コードを更新してGitにプッシュすると、Render.comが自動的に再デプロイします:

```bash
git add .
git commit -m "Update application"
git push origin main
```

## 参考リンク

- [Render.com Documentation](https://render.com/docs)
- [LINE Messaging API Documentation](https://developers.line.biz/ja/docs/messaging-api/)
