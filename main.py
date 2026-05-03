import os
from dotenv import load_dotenv
from emo_platform import Client, Head

# .env ファイルからトークンを自動で読み込む
load_dotenv()

# クライアントの初期化 (引数なしでOK！)
client = Client()

print("=== 情報を取得します ===")

# 自分のアカウント情報を取得して表示
print("アカウント情報:", client.get_account_info())

# BOCCO emoで使えるスタンプの一覧を表示
print("スタンプ一覧:", client.get_stamps_list())

# 部屋の情報を取得して操作の準備をする
room_id_list = client.get_rooms_id()

if not room_id_list:
    print("エラー: 部屋が見つかりません。")
    exit()

# 最初の部屋を操作するための「ルームクライアント」を作成
room_client = client.create_room_client(room_id_list[1])

# 部屋に投稿されたメッセージ履歴を取得
print("メッセージ履歴:", room_client.get_msgs())

# BOCCO emoを動かす
print("BOCCO emoの首を動かします...")
room_client.move_to(Head(10, 10))