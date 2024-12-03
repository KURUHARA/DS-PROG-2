import flet as ft
import requests
import json
import os
from datetime import datetime
from collections import defaultdict

# メインUIのカラー定義
COLORS = {
    'primary': '#1976D2',         # メインカラー（青）
    'secondary': '#424242',       # テキストカラー
    'background': '#F5F5F5',      # 背景色
    'card': '#FFFFFF',            # カード背景
    'accent': '#2196F3',         # アクセントカラー
    'error': '#D32F2F',          # エラー表示
    'success': '#4CAF50',        # 成功表示
    'warning': '#FFA000',        # 警告表示
    'header_bg': '#E3F2FD',      # ヘッダー背景
    'divider': '#BDBDBD',        # 区切り線
}

# 天気予報アイコンの色定義
WEATHER_COLORS = {
    'temp_hot': '#F44336',      # 高温
    'temp_cold': '#2196F3',     # 低温
    'rain': '#1565C0',          # 雨関連
    'cloud': '#757575',         # 曇り関連
    'wind': '#78909C',          # 風関連
}

class WeatherApp:
    def __init__(self):
        self.areas = {}
        self.area_groups = {}
        self.selected_area = None
        self.forecast_data = None
        self.selected_view = "forecast"
        
        self.script_dir = os.path.dirname(__file__)
        self.area_json_path = os.path.join(self.script_dir, 'areas.json')
        
        # 特別な地域コードのマッピング
        self.area_code_mapping = {
            "014030": "014100"  # 十勝地方
        }

    def main(self, page: ft.Page):
        page.title = "天気予報アプリ"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 20
        page.window_width = 1000
        page.window_height = 700
        page.scroll = ft.ScrollMode.AUTO
        page.bgcolor = COLORS['background']

        self.nav_rail = ft.Container(
            content=ft.NavigationRail(
                selected_index=0,
                label_type=ft.NavigationRailLabelType.ALL,
                min_width=100,
                min_extended_width=200,
                destinations=[
                    ft.NavigationRailDestination(
                        icon=ft.icons.CLOUD_OUTLINED,
                        selected_icon=ft.icons.CLOUD,
                        label="天気予報",
                        selected_icon_content=ft.Icon(ft.icons.CLOUD, color=COLORS['primary'])
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.icons.LOCATION_ON_OUTLINED,
                        selected_icon=ft.icons.LOCATION_ON,
                        label="地域一覧",
                        selected_icon_content=ft.Icon(ft.icons.LOCATION_ON, color=COLORS['primary'])
                    ),
                ],
                on_change=self.on_nav_change,
                bgcolor=COLORS['card']
            ),
            height=700,
        )

        self.area_dropdown = ft.Dropdown(
            label="地域を選択",
            width=400,
            on_change=self.on_area_selected,
            border_color=COLORS['primary'],
            label_style=ft.TextStyle(color=COLORS['secondary'])
        )

        self.forecast_container = ft.Container(
            content=None,
            padding=10,
            height=500,
            bgcolor=COLORS['card'],
        )

        self.area_list_container = ft.Container(
            content=None,
            padding=10,
            visible=False,
            height=500,
            bgcolor=COLORS['card'],
        )

        self.loading = ft.ProgressRing(
            visible=False,
            color=COLORS['primary']
        )

        self.error_text = ft.Text(
            color=COLORS['error'],
            size=14,
            visible=False
        )

        # メインヘッダー
        header = ft.Container(
            content=ft.Text(
                "気象庁天気予報",
                size=24,
                weight=ft.FontWeight.BOLD,
                color=COLORS['primary']
            ),
            bgcolor=COLORS['header_bg'],
            padding=15,
            border_radius=10,
        )

        main_column = ft.Column(
            controls=[
                header,
                self.area_dropdown,
                self.loading,
                self.error_text,
                ft.Container(
                    content=ft.Column(
                        controls=[
                            self.forecast_container,
                            self.area_list_container
                        ],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    height=500,
                    border=ft.border.all(1, COLORS['divider']),
                    border_radius=10,
                    padding=10,
                    bgcolor=COLORS['card'],
                ),
            ],
            spacing=20,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        self.content = ft.Row(
            controls=[
                self.nav_rail,
                ft.VerticalDivider(width=1, color=COLORS['divider']),
                main_column
            ],
            expand=True,
        )

        page.add(self.content)
        self.load_areas()

    def load_areas(self):
        try:
            with open(self.area_json_path, 'r', encoding='utf-8') as file:
                area_data = json.load(file)
            
            self.areas = {**area_data.get("centers", {}), **area_data.get("offices", {})}
            self.area_groups = self.group_areas(area_data)
            self.update_dropdown_options()
            self.update_area_list()

        except FileNotFoundError:
            self.show_error(f"areas.jsonファイルが見つかりません\nパス: {self.area_json_path}")
        except json.JSONDecodeError:
            self.show_error("JSONファイルの形式が正しくありません")
        except Exception as e:
            self.show_error(f"エラーが発生しました: {str(e)}")

    def group_areas(self, area_data):
        groups = {}
        centers = area_data.get("centers", {})
        offices = area_data.get("offices", {})

        for center_code, center in centers.items():
            groups[center_code] = {
                "info": center,
                "children": {}
            }

        for office_code, office in offices.items():
            parent_code = office.get("parent", "")
            if parent_code in groups:
                groups[parent_code]["children"][office_code] = office

        return groups

    def update_dropdown_options(self):
        options = []
        
        for center_code, group in self.area_groups.items():
            center = group["info"]
            options.append(ft.dropdown.Option(
                key=f"group_{center_code}",
                text=f"【{center['name']}】",
                disabled=True
            ))
            
            for office_code, office in group["children"].items():
                options.append(ft.dropdown.Option(
                    key=office_code,
                    text=f"  {office['name']}"
                ))

        self.area_dropdown.options = options
        self.area_dropdown.update()

    def update_area_list(self):
        area_list = []
        
        for center_code, group in self.area_groups.items():
            center = group["info"]
            
            center_header = ft.Container(
                content=ft.Text(
                    center["name"],
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS['primary']
                ),
                bgcolor=COLORS['header_bg'],
                padding=10,
                border_radius=5,
                margin=ft.margin.only(top=10)
            )
            area_list.append(center_header)
            
            for office_code, office in group["children"].items():
                office_tile = ft.ListTile(
                    leading=ft.Icon(ft.icons.LOCATION_ON, color=COLORS['primary']),
                    title=ft.Text(office["name"], color=COLORS['secondary']),
                    subtitle=ft.Text(f"地域コード: {office_code}"),
                    on_click=lambda e, code=office_code: self.on_area_selected_from_list(code)
                )
                area_list.append(office_tile)

        self.area_list_container.content = ft.ListView(
            controls=area_list,
            spacing=2,
            padding=20,
            auto_scroll=True
        )
        self.area_list_container.update()

    def fetch_forecast(self, area_code: str):
        try:
            self.loading.visible = True
            self.loading.update()
            
            mapped_code = self.area_code_mapping.get(area_code, area_code)
            
            url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{mapped_code}.json"
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                raise ValueError("データが空です")
                
            self.forecast_data = data[0]
            self.update_forecast_display()
            
        except requests.exceptions.RequestException as e:
            self.show_error(f"天気予報の取得に失敗しました\nネットワークエラー: {str(e)}")
        except json.JSONDecodeError as e:
            self.show_error(f"天気予報データの解析に失敗しました\nJSONエラー: {str(e)}")
        except IndexError as e:
            self.show_error("天気予報データの形式が不正です")
        except Exception as e:
            self.show_error(f"エラーが発生しました: {str(e)}")
        finally:
            self.loading.visible = False
            self.loading.update()

    def update_forecast_display(self):
        if not self.forecast_data:
            return

        area_forecasts = []

        if report_time := self.forecast_data.get("reportDatetime"):
            report_time = datetime.fromisoformat(report_time.replace("Z", "+00:00"))
            time_header = ft.Container(
                content=ft.Text(
                    f"予報時刻: {report_time.strftime('%Y年%m月%d日 %H時%M分')}",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS['secondary']
                ),
                bgcolor=COLORS['header_bg'],
                padding=10,
                border_radius=5,
                margin=ft.margin.only(bottom=10)
            )
            area_forecasts.append(time_header)

        for time_series in self.forecast_data["timeSeries"]:
            timeDefines = time_series.get("timeDefines", [])
            
            for area in time_series["areas"]:
                area_name = area["area"]["name"]
                forecast_controls = []

                if timeDefines:
                    try:
                        times = [datetime.fromisoformat(t.replace("Z", "+00:00")) for t in timeDefines]
                        if times:
                            forecast_controls.append(
                                ft.ListTile(
                                    leading=ft.Icon(ft.icons.ACCESS_TIME, color=COLORS['secondary']),
                                    title=ft.Text("予報期間", color=COLORS['secondary']),
                                    subtitle=ft.Text(
                                        f"{times[0].strftime('%m/%d %H時')} ～ {times[-1].strftime('%m/%d %H時')}"
                                    )
                                )
                            )
                    except Exception:
                        pass

                weathers = area.get("weathers", [])
                if weathers and weathers[0]:
                    forecast_controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.CLOUD, color=WEATHER_COLORS['cloud']),
                            title=ft.Text("天気", color=COLORS['secondary']),
                            subtitle=ft.Text(weathers[0])
                        )
                    )

                temps = area.get("temps", [])
                if temps and any(temps):
                    temp_text = []
                    if temps[0]:
                        temp_text.append(f"最高: {temps[0]}℃")
                    if len(temps) > 1 and temps[1]:
                        temp_text.append(f"最低: {temps[1]}℃")
                    if temp_text:
                        forecast_controls.append(
                            ft.ListTile(
                                leading=ft.Icon(
                                    ft.icons.THERMOSTAT,
                                    color=WEATHER_COLORS['temp_hot'] if temps[0] and float(temps[0]) > 25 else WEATHER_COLORS['temp_cold']
                                ),
                                title=ft.Text("気温", color=COLORS['secondary']),
                                subtitle=ft.Text(" / ".join(temp_text))
                            )
                        )

                pops = area.get("pops", [])
                if pops and pops[0]:
                    forecast_controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.WATER_DROP, color=WEATHER_COLORS['rain']),
                            title=ft.Text("降水確率", color=COLORS['secondary']),
                            subtitle=ft.Text(f"{pops[0]}%")
                        )
                    )

                winds = area.get("winds", [])
                wind_levels = area.get("windLevels", [])
                if (winds and winds[0]) or (wind_levels and wind_levels[0]):
                    wind_text = []
                    if winds and winds[0]:
                        wind_text.append(f"風向: {winds[0]}")
                    if wind_levels and wind_levels[0]:
                        wind_text.append(f"風速: {wind_levels[0]}")
                    if wind_text:
                        forecast_controls.append(
                            ft.ListTile(
                                leading=ft.Icon(ft.icons.AIR, color=WEATHER_COLORS['wind']),
                                title=ft.Text("風", color=COLORS['secondary']),
                                subtitle=ft.Text(" / ".join(wind_text))
                            )
                        )

                if forecast_controls:
                    forecast_tile = ft.ExpansionTile(
                        title=ft.Text(f"{area_name}の予報", color=COLORS['primary']),
                        subtitle=ft.Text(weathers[0] if weathers else ""),
                        controls=forecast_controls,
                        bgcolor=COLORS['header_bg'],
                    )
                    tile_container = ft.Container(
                        content=forecast_tile,
                        margin=ft.margin.only(bottom=5),
                        border_radius=5,
                    )
                    area_forecasts.append(tile_container)

        if area_forecasts:
            self.forecast_container.content = ft.ListView(
                controls=area_forecasts,
                spacing=2,
                padding=20,
                auto_scroll=True
            )
            self.forecast_container.update()
        else:
            self.forecast_container.content = ft.Text(
                "予報データがありません",
                color=COLORS['error']
            )
            self.forecast_container.update()

    def on_area_selected(self, e):
        if e.data and not e.data.startswith("group_"):
            self.selected_area = e.data
            self.fetch_forecast(e.data)

    def on_area_selected_from_list(self, code):
        self.area_dropdown.value = code
        self.area_dropdown.update()
        self.selected_area = code
        self.fetch_forecast(code)
        self.show_forecast_view()

    def on_nav_change(self, e):
        self.selected_view = "forecast" if e.control.selected_index == 0 else "areas"
        self.update_view()

    def update_view(self):
        if self.selected_view == "forecast":
            self.show_forecast_view()
        else:
            self.show_area_list_view()

    def show_forecast_view(self):
        self.forecast_container.visible = True
        self.area_list_container.visible = False
        self.area_dropdown.visible = True
        self.update()

    def show_area_list_view(self):
        self.forecast_container.visible = False
        self.area_list_container.visible = True
        self.area_dropdown.visible = False
        self.update()

    def show_error(self, message: str):
        self.error_text.value = message
        self.error_text.color = COLORS['error']
        self.error_text.visible = True
        self.error_text.update()

    def update(self):
        self.forecast_container.update()
        self.area_list_container.update()
        self.area_dropdown.update()

# プログラムのエントリーポイント
def main():
    app = WeatherApp()
    ft.app(target=app.main)

if __name__ == "__main__":
    main()