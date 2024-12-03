import json
import os

# 現在のスクリプトのディレクトリを取得
script_dir = os.path.dirname(__file__)

# jmaディレクトリ内のarea.jsonの絶対パスを作成
area_json_path = os.path.join(script_dir, 'areas.json')

# area.jsonを開く
with open(area_json_path, 'r', encoding='utf-8') as file:
    area_data = json.load(file)

# データの内容を表示して確認
print(json.dumps(area_data, indent=4, ensure_ascii=False))