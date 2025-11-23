# LINEリッチメニューへの予約・管理画面追加ガイド

このガイドでは、予約フォームとセラピスト管理画面をLINEリッチメニューに追加する方法を説明します。

---

## 1. 客用アカウント - 予約ボタンの追加

### 方法1: テキストアクションで追加(推奨)

既存のリッチメニューに「予約する」ボタンを追加します。

#### 手順:
1. [LINE Official Account Manager](https://manager.line.biz/)にログイン
2. 客用アカウントを選択
3. 「ホーム」→「トークルーム管理」→「リッチメニュー」
4. 既存のメニューを編集、または新規作成
5. **アクション設定**で新しいボタンを追加:
   - タイプ: **テキスト**
   - テキスト: `予約する`

#### main.pyの対応コード:
```python
@handler_customer.add(MessageEvent, message=TextMessage)
def handle_message_customer(event):
    text = event.message.text
    user_id = event.source.user_id
    
    if text == "予約する":
        # Send Booking Link
        base_url = request.url_root.replace('http://', 'https://')
        booking_url = f"{base_url}booking?userId={user_id}"
        
        line_bot_api_customer.reply_message(
            event.reply_token,
            TemplateSendMessage(
                alt_text='予約画面を開く',
                template=ButtonsTemplate(
                    title='予約',
                    text='以下のボタンから予約してください',
                    actions=[
                        URIAction(
                            label='予約画面を開く',
                            uri=booking_url
                        )
                    ]
                )
            )
        )
```

このコードは既に実装済みです(main.py:284-304)。

### 方法2: URLアクションで直接リンク

リッチメニューから直接予約画面を開きたい場合:

#### 手順:
1. リッチメニューのアクション設定で:
   - タイプ: **リンク**
   - URL: `https://あなたのドメイン/booking?userId={userId}`
   
> **注意**: `{userId}`は自動的にユーザーのLINE IDに置き換わります。ただし、この方法ではLIFFの初期化が必要になる場合があります。

---

## 2. セラピスト用アカウント - 管理画面ボタンの追加

### 方法1: テキストアクションで追加(推奨)

#### 手順:
1. セラピスト用アカウントに切り替え
2. 「リッチメニュー」→既存メニューを編集または新規作成
3. **アクション設定**で新しいボタンを追加:
   - タイプ: **テキスト**
   - テキスト: `管理`

#### main.pyの対応コード:
```python
@handler_therapist.add(MessageEvent, message=TextMessage)
def handle_message_therapist(event):
    user_id = event.source.user_id
    text = event.message.text

    if text == "管理":
        # Send Dashboard Link
        base_url = request.url_root.replace('http://', 'https://')
        dashboard_url = f"{base_url}therapist/dashboard"
        
        line_bot_api_therapist.reply_message(
            event.reply_token,
            TemplateSendMessage(
                alt_text='管理画面を開く',
                template=ButtonsTemplate(
                    title='管理',
                    text='以下のボタンから管理画面を開いてください',
                    actions=[
                        URIAction(
                            label='管理画面を開く',
                            uri=dashboard_url
                        )
                    ]
                )
            )
        )
```

このコードも既に実装済みです(main.py:344-364)。

### 方法2: URLアクションで直接リンク

#### 手順:
1. リッチメニューのアクション設定で:
   - タイプ: **リンク**
   - URL: `https://あなたのドメイン/therapist/dashboard`

---

## 3. 推奨リッチメニュー構成

### 客用アカウント(3ボタン構成)

```
┌─────────┬─────────┬─────────┐
│ 予約する │ 料金表  │ 出勤表  │
└─────────┴─────────┴─────────┘
```

**アクション設定:**
- ボタン1: テキスト「予約する」
- ボタン2: テキスト「料金表」
- ボタン3: テキスト「出勤表」

### セラピスト用アカウント(3ボタン構成)

```
┌─────────────┬─────────────┐
│    管理     │ 出勤情報登録 │
├─────────────┴─────────────┤
│        (予備)             │
└───────────────────────────┘
```

**アクション設定:**
- ボタン1: テキスト「管理」
- ボタン2: テキスト「出勤情報登録」
- ボタン3: (将来の機能用に予備)

---

## 4. テスト方法

### 客用アカウント:
1. LINEで客用アカウントを友だち追加
2. リッチメニューの「予約する」をタップ
3. ボットから予約画面のリンクが送られてくることを確認
4. リンクをタップして予約画面が開くことを確認

### セラピスト用アカウント:
1. LINEでセラピスト用アカウントを友だち追加
2. リッチメニューの「管理」をタップ
3. ボットから管理画面のリンクが送られてくることを確認
4. リンクをタップして管理画面が開くことを確認

---

## 5. よくある質問

### Q: なぜテキストアクションを使うのですか?
A: テキストアクションを使うことで、ボットが応答を返すことができます。これにより、動的にURLを生成したり、ユーザーIDを含めたりすることが可能になります。

### Q: URLアクションとテキストアクションの違いは?
A: 
- **URLアクション**: リッチメニューから直接Webページを開く
- **テキストアクション**: ボットにメッセージを送り、ボットが応答を返す(より柔軟)

### Q: 本番環境(Render.com)で使う場合は?
A: `base_url`を本番環境のURLに変更する必要があります。環境変数で管理することを推奨します:

```python
# config.py
BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')

# main.py
base_url = Config.BASE_URL
booking_url = f"{base_url}/booking?userId={user_id}"
```

---

## 6. リッチメニュー画像の作成

リッチメニューには背景画像が必要です。

### 推奨サイズ:
- **大サイズ**: 2500 x 1686 px
- **小サイズ**: 2500 x 843 px

### 作成ツール:
- Canva (無料テンプレートあり)
- Adobe Photoshop
- LINE公式の[リッチメニュー画像作成ツール](https://www.linebiz.com/jp/service/line-official-account/rich-menu/)

### デザインのポイント:
- ボタンの境界を明確に
- テキストは大きく読みやすく
- ブランドカラーを使用
- アイコンを活用

---

## まとめ

1. **客用アカウント**: 「予約する」ボタンを追加(テキストアクション推奨)
2. **セラピスト用アカウント**: 「管理」ボタンを追加(テキストアクション推奨)
3. 既存のコードは実装済みなので、リッチメニューの設定のみで動作します
4. テスト環境で動作確認後、本番環境にデプロイ
