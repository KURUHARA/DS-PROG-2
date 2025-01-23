import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def scrape_jnto_visitors():
    # JNTOの統計ページのURL
    base_url = "https://statistics.jnto.go.jp/en/graph/#graph--inbound--travelers--transition"
    
    try:
        # ページの取得
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        
        # BeautifulSoupでHTMLをパース
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # データを格納するリスト
        visitors_data = []
        
        # データテーブルの取得
        table = soup.find('table', {'class': 'data-table'})
        if table:
            rows = table.find_all('tr')
            
            # 各行のデータを処理
            for row in rows[1:]:  # ヘッダーをスキップ
                cols = row.find_all('td')
                if cols:
                    year = cols[0].text.strip()
                    visitors = int(cols[1].text.strip().replace(',', ''))
                    visitors_data.append({
                        'Year': year,
                        'Visitors': visitors
                    })
        
        # DataFrameに変換
        df = pd.DataFrame(visitors_data)
        
        # CSVファイルとして保存
        df.to_csv('jnto_visitors.csv', index=False)
        print("データの取得が完了しました。'jnto_visitors.csv'として保存されました。")
        
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"エラーが発生しました: {e}")
        return None

# 実行
if __name__ == "__main__":
    print("JNTOの訪日外客数データの取得を開始します...")
    df = scrape_jnto_visitors()
    if df is not None:
        print("\nデータサンプル:")
        print(df.head())
