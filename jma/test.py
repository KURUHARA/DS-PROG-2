import flet as ft
import requests
import json
import os
from datetime import datetime

class WeatherApp:
    def __init__(self):
        self.areas = {}
        self.selected_area = None
        self.forecast_data = None
        self.selected_view = "forecast"
        # スクリプトのディレクトリパスを保存
        self.script_dir = os.path.dirname(__file__)
        # areas.jsonの絶対パスを作成
        self.area_json_path = os.path.join(self.script_dir, 'areas.json')

    def main(self, page: ft.Page):
        page.title = "天気予報アプリ"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 20
        page.window_width = 1000
        page.window_height = 700

        # ナビゲーションレール
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.icons.CLOUD_OUTLINED,
                    selected_icon=ft.icons.CLOUD,
                    label="天気予報"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.LOCATION_ON_OUTLINED,
                    selected_icon=ft.icons.LOCATION_ON,
                    label="地域一覧"
                ),
            ],
            on_change=self.on_nav_change
        )

        # エリア選択ドロップダウン
        self.area_dropdown = ft.Dropdown(
            label="地域を選択",
            width=400,
            on_change=self.on_area_selected
        )

        # 天気予報表示用のコンテナ
        self.forecast_container = ft.Container(
            content=None,
            padding=10
        )

        # 地域一覧表示用のコンテナ
        self.area_list_container = ft.Container(
            content=None,
            padding=10,
            visible=False
        )

        # ローディング表示
        self.loading = ft.ProgressRing(visible=False)

        # エラーメッセージ表示
        self.error_text = ft.Text(
            color="red",
            size=14,
            visible=False
        )

        # メインコンテンツ
        self.content = ft.Row(
            controls=[
                self.nav_rail,
                ft.VerticalDivider(width=1),
                ft.Column(
                    controls=[
                        ft.Text("気象庁天気予報", size=24, weight=ft.FontWeight.BOLD),
                        self.area_dropdown,
                        self.loading,
                        self.error_text,
                        self.forecast_container,
                        self.area_list_container
                    ],
                    spacing=20,
                    expand=True
                )
            ],
            expand=True
        )

        page.add(self.content)

        # 地域データの初期読み込み
        self.load_areas()

    def load_areas(self):
        """ローカルのJSONファイルから地域データを読み込む"""
        try:
            with open(self.area_json_path, 'r', encoding='utf-8') as file:
                area_data = json.load(file)
                self.areas = area_data["offices"]
            
            # ドロップダウンの選択肢を更新
            self.area_dropdown.options = [
                ft.dropdown.Option(key=code, text=area["name"])
                for code, area in self.areas.items()
            ]
            self.area_dropdown.update()

            # 地域一覧の作成
            self.update_area_list()

        except FileNotFoundError:
            self.show_error(f"areas.jsonファイルが見つかりません\nパス: {self.area_json_path}")
        except json.JSONDecodeError:
            self.show_error("JSONファイルの形式が正しくありません")
        except Exception as e:
            self.show_error(f"エラーが発生しました: {str(e)}")

    def fetch_forecast(self, area_code: str):
        """天気予報データを取得"""
        try:
            self.loading.visible = True
            self.loading.update()
            
            response = requests.get(f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json")
            self.forecast_data = response.json()[0]
            self.update_forecast_display()
        except Exception as e:
            self.show_error("天気予報の取得に失敗しました")
        finally:
            self.loading.visible = False
            self.loading.update()

    def update_forecast_display(self):
        """天気予報の表示を更新"""
        if not self.forecast_data:
            return

        area_forecasts = []
        
        # 予報データの整理と表示
        for time_series in self.forecast_data["timeSeries"]:
            for area in time_series["areas"]:
                # ExpansionTileで予報を表示
                forecast_tile = ft.ExpansionTile(
                    title=ft.Text(f"{area['area']['name']}の予報"),
                    subtitle=ft.Text(
                        area.get("weathers", ["データなし"])[0] 
                        if "weathers" in area else "気温データ"
                    ),
                    controls=[
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.CLOUD),
                            title=ft.Text("天気"),
                            subtitle=ft.Text(
                                area.get("weathers", ["データなし"])[0] 
                                if "weathers" in area else "データなし"
                            )
                        ),
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.THERMOSTAT),
                            title=ft.Text("気温"),
                            subtitle=ft.Text(
                                f"最高: {area.get('temps', ['--'])[0]}℃" 
                                if "temps" in area else "データなし"
                            )
                        ),
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.WATER_DROP),
                            title=ft.Text("降水確率"),
                            subtitle=ft.Text(
                                f"{area.get('pops', ['--'])[0]}%" 
                                if "pops" in area else "データなし"
                            )
                        )
                    ]
                )
                area_forecasts.append(forecast_tile)

        # 予報表示の更新
        self.forecast_container.content = ft.Column(
            controls=area_forecasts,
            scroll=ft.ScrollMode.AUTO
        )
        self.forecast_container.update()

    def update_area_list(self):
        """地域一覧の表示を更新"""
        area_list = []
        
        for code, area in self.areas.items():
            area_tile = ft.ListTile(
                leading=ft.Icon(ft.icons.LOCATION_ON),
                title=ft.Text(area["name"]),
                subtitle=ft.Text(f"地域コード: {code}"),
                on_click=lambda e, code=code: self.on_area_selected_from_list(code)
            )
            area_list.append(area_tile)

        self.area_list_container.content = ft.Column(
            controls=area_list,
            scroll=ft.ScrollMode.AUTO
        )
        self.area_list_container.update()

    def on_area_selected(self, e):
        """ドロップダウンでの地域選択時の処理"""
        if e.data:
            self.selected_area = e.data
            self.fetch_forecast(e.data)

    def on_area_selected_from_list(self, code):
        """地域一覧からの選択時の処理"""
        self.area_dropdown.value = code
        self.area_dropdown.update()
        self.selected_area = code
        self.fetch_forecast(code)
        self.show_forecast_view()

    def on_nav_change(self, e):
        """ナビゲーションの変更時の処理"""
        self.selected_view = "forecast" if e.control.selected_index == 0 else "areas"
        self.update_view()

    def update_view(self):
        """表示の切り替え"""
        if self.selected_view == "forecast":
            self.show_forecast_view()
        else:
            self.show_area_list_view()

    def show_forecast_view(self):
        """天気予報ビューの表示"""
        self.forecast_container.visible = True
        self.area_list_container.visible = False
        self.area_dropdown.visible = True
        self.update()

    def show_area_list_view(self):
        """地域一覧ビューの表示"""
        self.forecast_container.visible = False
        self.area_list_container.visible = True
        self.area_dropdown.visible = False
        self.update()

    def show_error(self, message: str):
        """エラーメッセージの表示"""
        self.error_text.value = message
        self.error_text.visible = True
        self.error_text.update()

    def update(self):
        """全体の表示を更新"""
        self.forecast_container.update()
        self.area_list_container.update()
        self.area_dropdown.update()

def main():
    app = WeatherApp()
    ft.app(target=app.main)

if __name__ == "__main__":
    main()