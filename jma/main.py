# weather_app.py

import flet as ft
import requests
import json
import os
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional
from dataclasses import dataclass

# メインUIのカラー定義
COLORS = {
    'primary': '#1976D2',
    'secondary': '#424242',
    'background': '#F5F5F5',
    'card': '#FFFFFF',
    'accent': '#2196F3',
    'error': '#D32F2F',
    'success': '#4CAF50',
    'warning': '#FFA000',
    'header_bg': '#E3F2FD',
    'divider': '#BDBDBD',
}

# 天気予報アイコンの色定義
WEATHER_COLORS = {
    'temp_hot': '#F44336',
    'temp_cold': '#2196F3',
    'rain': '#1565C0',
    'cloud': '#757575',
    'wind': '#78909C',
}

@dataclass
class WeatherForecast:
    area_code: str
    area_name: str
    forecast_date: datetime
    report_datetime: datetime
    weather: str
    temperature_high: Optional[float]
    temperature_low: Optional[float]
    precipitation_probability: Optional[int]
    wind_direction: Optional[str]
    wind_speed: Optional[str]

class WeatherDatabase:
    def __init__(self, db_path: str = "weather.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """データベースとテーブルの初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # エリアマスターテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS areas (
                    area_code TEXT PRIMARY KEY,
                    area_name TEXT NOT NULL,
                    parent_area_code TEXT,
                    area_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_area_code) REFERENCES areas (area_code)
                )
            ''')
            
            # 天気予報テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weather_forecasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    area_code TEXT NOT NULL,
                    forecast_date DATE NOT NULL,
                    report_datetime TIMESTAMP NOT NULL,
                    weather TEXT,
                    temperature_high REAL,
                    temperature_low REAL,
                    precipitation_probability INTEGER,
                    wind_direction TEXT,
                    wind_speed TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (area_code) REFERENCES areas (area_code),
                    UNIQUE (area_code, forecast_date, report_datetime)
                )
            ''')
            
            # インデックス作成
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_forecasts_area_date 
                ON weather_forecasts (area_code, forecast_date)
            ''')
            
            conn.commit()

    def save_area(self, area_code: str, area_name: str, parent_area_code: Optional[str], area_type: str):
        """エリア情報の保存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO areas 
                (area_code, area_name, parent_area_code, area_type, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (area_code, area_name, parent_area_code, area_type))
            conn.commit()

    def save_forecast(self, forecast: WeatherForecast):
        """天気予報データの保存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO weather_forecasts 
                (area_code, forecast_date, report_datetime, weather, 
                temperature_high, temperature_low, precipitation_probability,
                wind_direction, wind_speed, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                forecast.area_code,
                forecast.forecast_date.date(),
                forecast.report_datetime,
                forecast.weather,
                forecast.temperature_high,
                forecast.temperature_low,
                forecast.precipitation_probability,
                forecast.wind_direction,
                forecast.wind_speed
            ))
            conn.commit()

    def get_forecasts(self, area_code: str, target_date: datetime) -> List[WeatherForecast]:
        """指定日の天気予報データを取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT f.area_code, f.forecast_date, f.report_datetime, 
                       a.area_name, f.weather, f.temperature_high, 
                       f.temperature_low, f.precipitation_probability,
                       f.wind_direction, f.wind_speed
                FROM weather_forecasts f
                JOIN areas a ON f.area_code = a.area_code
                WHERE f.area_code = ?
                AND DATE(f.forecast_date) = DATE(?)
                ORDER BY f.report_datetime DESC
            ''', (area_code, target_date.date()))
            
            forecasts = []
            for row in cursor.fetchall():
                forecasts.append(WeatherForecast(
                    area_code=row[0],
                    area_name=row[3],
                    forecast_date=datetime.strptime(row[1], '%Y-%m-%d'),
                    report_datetime=datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S'),
                    weather=row[4],
                    temperature_high=row[5],
                    temperature_low=row[6],
                    precipitation_probability=row[7],
                    wind_direction=row[8],
                    wind_speed=row[9]
                ))
            return forecasts

    def get_all_areas(self) -> Dict[str, Dict]:
        """全てのエリア情報を取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT area_code, area_name, parent_area_code, area_type
                FROM areas
                ORDER BY area_type, area_code
            ''')
            
            areas = {}
            for row in cursor.fetchall():
                areas[row[0]] = {
                    'name': row[1],
                    'parent': row[2],
                    'type': row[3]
                }
            return areas

    def import_areas_from_json(self, json_path: str):
        """エリア情報をJSONファイルからインポート"""
        with open(json_path, 'r', encoding='utf-8') as f:
            area_data = json.load(f)
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # センター情報の保存
            for code, center in area_data.get("centers", {}).items():
                self.save_area(code, center["name"], None, "center")
            
            # 事務所情報の保存
            for code, office in area_data.get("offices", {}).items():
                self.save_area(code, office["name"], office.get("parent"), "office")
            
            conn.commit()

class WeatherApp:
    def __init__(self):
        self.db = WeatherDatabase()
        self.areas = {}
        self.area_groups = {}
        self.selected_area = None
        self.forecast_data = None
        self.selected_view = "forecast"
        self.selected_date = datetime.now()
        
        self.script_dir = os.path.dirname(__file__)
        self.area_json_path = os.path.join(self.script_dir, 'areas.json')
        
        self.area_code_mapping = {
            "014030": "014100"  # 十勝地方
        }

    def main(self, page: ft.Page):
        page.title = "天気予報アプリ"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 20
        page.window.width = 1000
        page.window.height = 700
        page.scroll = ft.ScrollMode.AUTO
        page.bgcolor = COLORS['background']

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

        # ナビゲーションレール
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
                    ft.NavigationRailDestination(
                        icon=ft.icons.HISTORY_OUTLINED,
                        selected_icon=ft.icons.HISTORY,
                        label="履歴",
                        selected_icon_content=ft.Icon(ft.icons.HISTORY, color=COLORS['primary'])
                    ),
                ],
                on_change=self.on_nav_change,
                bgcolor=COLORS['card']
            ),
            height=700,
        )

        # エリア選択ドロップダウン
        self.area_dropdown = ft.Dropdown(
            label="地域を選択",
            width=400,
            on_change=self.on_area_selected,
            border_color=COLORS['primary'],
            label_style=ft.TextStyle(color=COLORS['secondary'])
        )

        # 日付選択
        self.date_picker = ft.DatePicker(
            on_change=self.on_date_selected,
            first_date=datetime.now() - timedelta(days=365),
            last_date=datetime.now(),
        )
        page.overlay.append(self.date_picker)

        # 日付選択ボタン
        self.date_button = ft.ElevatedButton(
            "日付選択",
            icon=ft.icons.CALENDAR_TODAY,
            on_click=lambda _: self.date_picker.pick_date(),
            disabled=True
        )

        # コンテナー
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

        self.history_container = ft.Container(
            content=None,
            padding=10,
            visible=False,
            height=500,
            bgcolor=COLORS['card'],
        )

        # ローディングとエラー表示
        self.loading = ft.ProgressRing(
            visible=False,
            color=COLORS['primary']
        )

        self.error_text = ft.Text(
            color=COLORS['error'],
            size=14,
            visible=False
        )

        # コントロールバー
        control_bar = ft.Row(
            controls=[
                self.area_dropdown,
                self.date_button,
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=20,
        )

        # メインカラム
        main_column = ft.Column(
            controls=[
                header,
                control_bar,
                self.loading,
                self.error_text,
                ft.Container(
                    content=ft.Column(
                        controls=[
                            self.forecast_container,
                            self.area_list_container,
                            self.history_container
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

        # メインコンテンツ
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
        """エリア情報の読み込み"""
        try:
            self.db.import_areas_from_json(self.area_json_path)
            self.areas = self.db.get_all_areas()
            self.area_groups = self.group_areas()
            self.update_dropdown_options()
            self.update_area_list()

        except FileNotFoundError:
            self.show_error(f"areas.jsonファイルが見つかりません\nパス: {self.area_json_path}")
        except json.JSONDecodeError:
            self.show_error("JSONファイルの形式が正しくありません")
        except Exception as e:
            self.show_error(f"エラーが発生しました: {str(e)}")

    def group_areas(self) -> Dict:
        """エリアをグループ化"""
        groups = defaultdict(lambda: {"info": None, "children": {}})
        
        for code, area in self.areas.items():
            if area['type'] == 'center':
                groups[code]["info"] = {"code": code, "name": area['name']}
            else:  # office
                parent_code = area['parent']
                if parent_code in groups:
                    groups[parent_code]["children"][code] = {
                        "code": code,
                        "name": area['name']
                    }
        
        return dict(groups)

    def fetch_forecast(self, area_code: str):
        """天気予報データの取得"""
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
            self.save_current_forecast()
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

    def save_current_forecast(self):
        """現在の天気予報データをDBに保存"""
        if not self.forecast_data:
            return
        
        report_datetime = datetime.fromisoformat(
            self.forecast_data["reportDatetime"].replace("Z", "+00:00")
        )
        
        for time_series in self.forecast_data["timeSeries"]:
            timeDefines = time_series.get("timeDefines", [])
            
            for area in time_series["areas"]:
                area_code = area["area"]["code"]
                area_name = area["area"]["name"]
                
                for i, time in enumerate(timeDefines):
                    forecast_date = datetime.fromisoformat(time.replace("Z", "+00:00"))
                    
                    forecast = WeatherForecast(
                        area_code=area_code,
                        area_name=area_name,
                        forecast_date=forecast_date,
                        report_datetime=report_datetime,
                        weather=area.get("weathers", [""])[i] if "weathers" in area else None,
                        temperature_high=float(area["temps"][i]) if "temps" in area and area["temps"][i] else None,
                        temperature_low=float(area["temps"][i+1]) if "temps" in area and len(area["temps"]) > i+1 and area["temps"][i+1] else None,
                        precipitation_probability=int(area["pops"][i]) if "pops" in area and area["pops"][i] else None,
                        wind_direction=area.get("winds", [""])[i] if "winds" in area else None,
                        wind_speed=area.get("windLevels", [""])[i] if "windLevels" in area else None
                    )
                    
                    self.db.save_forecast(forecast)

    def on_date_selected(self, e):
        """日付選択時の処理"""
        if not self.selected_area or not e.data:
            return
        
        selected_date = datetime.fromtimestamp(e.data.timestamp())
        self.selected_date = selected_date
        
        try:
            self.loading.visible = True
            self.loading.update()
            
            # 選択された日付の予報データを取得
            forecasts = self.db.get_forecasts(
                self.selected_area,
                selected_date
            )
            
            if forecasts:
                self.update_historical_display(forecasts)
                self.show_history_view()
            else:
                self.history_container.content = ft.Text(
                    f"{selected_date.strftime('%Y年%m月%d日')}の予報データはありません",
                    color=COLORS['error']
                )
                self.history_container.update()
                self.show_history_view()
            
        except Exception as e:
            self.show_error(f"履歴データの取得に失敗しました: {str(e)}")
        finally:
            self.loading.visible = False
            self.loading.update()

    def on_area_selected(self, e):
        """エリア選択時の処理"""
        if e.data and not e.data.startswith("group_"):
            self.selected_area = e.data
            self.fetch_forecast(e.data)
            self.date_button.disabled = False
            self.date_button.update()

    def update_forecast_display(self):
        """天気予報表示の更新"""
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

    def update_historical_display(self, forecasts: List[WeatherForecast]):
        """履歴データの表示更新"""
        if not forecasts:
            self.history_container.content = ft.Text(
                "履歴データがありません",
                color=COLORS['error']
            )
            self.history_container.update()
            return

        history_controls = []
        
        # 日付ヘッダー
        date_header = ft.Container(
            content=ft.Text(
                f"予報日: {self.selected_date.strftime('%Y年%m月%d日')}の予報履歴",
                size=16,
                weight=ft.FontWeight.BOLD,
                color=COLORS['primary']
            ),
            bgcolor=COLORS['header_bg'],
            padding=10,
            border_radius=5,
            margin=ft.margin.only(bottom=10)
        )
        history_controls.append(date_header)

        # 予報データの表示
        for forecast in forecasts:
            forecast_controls = []
            
            if forecast.weather:
                forecast_controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.CLOUD, color=WEATHER_COLORS['cloud']),
                        title=ft.Text("天気", color=COLORS['secondary']),
                        subtitle=ft.Text(forecast.weather)
                    )
                )

            if forecast.temperature_high is not None or forecast.temperature_low is not None:
                temp_text = []
                if forecast.temperature_high is not None:
                    temp_text.append(f"最高: {forecast.temperature_high}℃")
                if forecast.temperature_low is not None:
                    temp_text.append(f"最低: {forecast.temperature_low}℃")
                forecast_controls.append(
                    ft.ListTile(
                        leading=ft.Icon(
                            ft.icons.THERMOSTAT,
                            color=WEATHER_COLORS['temp_hot'] if forecast.temperature_high and forecast.temperature_high > 25 else WEATHER_COLORS['temp_cold']
                        ),
                        title=ft.Text("気温", color=COLORS['secondary']),
                        subtitle=ft.Text(" / ".join(temp_text))
                    )
                )

            if forecast.precipitation_probability is not None:
                forecast_controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.WATER_DROP, color=WEATHER_COLORS['rain']),
                        title=ft.Text("降水確率", color=COLORS['secondary']),
                        subtitle=ft.Text(f"{forecast.precipitation_probability}%")
                    )
                )

            if forecast.wind_direction or forecast.wind_speed:
                wind_text = []
                if forecast.wind_direction:
                    wind_text.append(f"風向: {forecast.wind_direction}")
                if forecast.wind_speed:
                    wind_text.append(f"風速: {forecast.wind_speed}")
                forecast_controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.AIR, color=WEATHER_COLORS['wind']),
                        title=ft.Text("風", color=COLORS['secondary']),
                        subtitle=ft.Text(" / ".join(wind_text))
                    )
                )

            report_time = ft.Text(
                f"予報発表時刻: {forecast.report_datetime.strftime('%H時%M分')}",
                size=12,
                color=COLORS['secondary']
            )
            forecast_controls.append(report_time)

            forecast_card = ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        controls=forecast_controls,
                        spacing=5
                    ),
                    padding=10
                ),
                margin=ft.margin.only(bottom=10)
            )
            history_controls.append(forecast_card)

        self.history_container.content = ft.ListView(
            controls=history_controls,
            spacing=2,
            padding=20,
            auto_scroll=True
        )
        self.history_container.update()

    def update_area_list(self):
        """エリア一覧の更新"""
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

    def update_dropdown_options(self):
        """ドロップダウンのオプション更新"""
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

    def show_error(self, message: str):
        """エラーメッセージの表示"""
        self.error_text.value = message
        self.error_text.visible = True
        self.error_text.update()

    def on_area_selected_from_list(self, code):
        """エリア一覧からの選択時の処理"""
        self.area_dropdown.value = code
        self.area_dropdown.update()
        self.selected_area = code
        self.fetch_forecast(code)
        self.date_button.disabled = False
        self.date_button.update()
        self.show_forecast_view()

    def show_forecast_view(self):
        """天気予報ビューの表示"""
        self.selected_view = "forecast"
        self.update_view()
        self.nav_rail.content.selected_index = 0
        self.nav_rail.content.update()

    def show_area_list_view(self):
        """エリア一覧ビューの表示"""
        self.selected_view = "areas"
        self.update_view()

    def show_history_view(self):
        """履歴ビューの表示"""
        self.selected_view = "history"
        self.update_view()

    def on_nav_change(self, e):
        """ナビゲーション変更時の処理"""
        selected_index = e.control.selected_index
        if selected_index == 0:
            self.selected_view = "forecast"
        elif selected_index == 1:
            self.selected_view = "areas"
        else:
            self.selected_view = "history"
        self.update_view()

    def update_view(self):
        """表示の更新"""
        self.forecast_container.visible = self.selected_view == "forecast"
        self.area_list_container.visible = self.selected_view == "areas"
        self.history_container.visible = self.selected_view == "history"
        self.area_dropdown.visible = self.selected_view in ["forecast", "history"]
        self.date_button.visible = self.selected_view == "history"
        self.update()

    def update(self):
        """UI全体の更新"""
        self.forecast_container.update()
        self.area_list_container.update()
        self.history_container.update()
        self.area_dropdown.update()
        self.date_button.update()

def main():
    """アプリケーションのメインエントリーポイント"""
    app = WeatherApp()
    ft.app(target=app.main)

if __name__ == "__main__":
    main()