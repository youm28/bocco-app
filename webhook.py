import os
import json
import http.server
from dotenv import load_dotenv
from emo_platform import Client, WebHook, EmoPlatformError

# --- 1. 準備 ---
load_dotenv()
webhook_url = os.getenv("WEBHOOK_URL")

if not webhook_url:
    print("エラー: .env に WEBHOOK_URL が設定されていません。")
    exit()

# クライアントの初期化（自動で.envからトークンを読み込みます）
client = Client()

# room_clientを作るために、部屋のIDを取得しておきます（後でBOCCOに喋らせるため）
try:
    room_id_list = client.get_rooms_id()
    room_client = client.create_room_client(room_id_list[1]) 
except Exception as e:
    print(f"部屋の取得に失敗しました: {e}")

# --- 2. Webhookの設定 ---
print(f"BOCCOサーバーにWebhook URLを登録しています... ({webhook_url})")
client.create_webhook_setting(WebHook(webhook_url))

# =========================================================
# --- 3. イベント発生時の処理（ここにやりたい事を書きます）---
# =========================================================

# ① アプリからメッセージ（テキストや音声）を受け取った時
@client.event('message.received')
def on_message(data):
    print("\n📩 BOCCOからメッセージを受信しました！")
    
    # データの種類（media）を確認する
    media_type = data.data.message.media
    
    if media_type == 'text':
        # テキストメッセージの場合
        try:
            # 辞書型（dict）から 'ja' を取り出す正しい書き方
            text = data.data.message.message.ja
            print(f"メッセージ内容: {text}")
            # 【発展】ゆくゆくは、ここでAIに「text」を渡して返事をもらいます！
        except KeyError:
            print("※テキストデータが見つかりませんでした。")
            
    elif media_type == 'stamp':
        print("💡 スタンプを受信しました（テキストはありません）。")
        
    elif media_type == 'audio':
        print("💡 音声メッセージを受信しました。")
        
    else:
        print(f"💡 その他のメッセージ（{media_type}）を受信しました。")

# ② BOCCO本体の「照度センサー」が反応した時（部屋が明るくなった/暗くなった等）
@client.event('illuminance.changed')
def on_illuminance_changed(data):
    print("\n💡 部屋の明るさが変化しました！")
    # 例: print(data) と書くと、何ルクスになったか詳細が見られます

# ③ 【別売り】人感センサー（レーダー）が反応した時
# ※ 公式仕様上、BOCCOの人感センサーは 'human_sensor.detected' というイベントで通知されます
@client.event('human_sensor.detected')
def on_human_detected(data):
    print("\n🚶 人感センサーが反応しました！（誰かが前を通りました）")
    # 【発展】ここで「おかえり！」と喋らせる処理などを書くことができます
    # センサーの名前を取り出してみる（例：「人感センサ」）
    sensor_name = data.data.human_sensor.user.nickname
    print(f"反応したセンサー: {sensor_name}")
    
    # ★ BOCCO emoに実際に喋らせる！
    print("BOCCOに「おかえり！」と喋らせます...")
    room_client.send_msg("誰か来たね！おかえりなさい！")

# =========================================================

# --- 4. Webhookの開始と暗号鍵の取得 ---
secret_key = client.start_webhook_event()
print("\n準備完了！ローカルサーバーを起動し、メッセージやセンサーの反応を待ち受けます...")

# --- 5. ローカルサーバー（受取窓口）の構築 ---
# ※ ここは「通信を受け取るための裏方の作業」なので、基本はいじらなくてOKです
class Handler(http.server.BaseHTTPRequestHandler):
    def _send_status(self, status):
        self.send_response(status)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()

    def do_POST(self):
        # セキュリティチェック: 偽物からのリクエストを弾く
        if not secret_key == self.headers.get("X-Platform-Api-Secret"):
            self._send_status(401)
            return

        # BOCCOサーバーから送られてきたデータを読み込む
        content_len = int(self.headers['content-length'])
        request_body = json.loads(self.rfile.read(content_len).decode('utf-8'))

        try:
            # SDKが自動で、どの関数を実行すべきか（今回は3つのどれか）を判断してくれる
            cb_func, emo_webhook_body = client.get_cb_func(request_body)
        except EmoPlatformError:
            self._send_status(501) # 知らないイベントは無視する
            return

        # 登録しておいた関数（on_message 等）を実行！
        cb_func(emo_webhook_body)

        # 正常に受け取ったことをBOCCOサーバーに報告
        self._send_status(200)
        
    # 余分なアクセスログを非表示にする（ターミナルを見やすくするため）
    def log_message(self, format, *args):
        pass

# 8000番ポートでサーバーを起動して待ち続ける
with http.server.HTTPServer(('', 8000), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止しました。")