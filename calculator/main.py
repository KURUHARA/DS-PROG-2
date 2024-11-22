import flet as ft
import math
from enum import Enum, auto
from typing import Callable, Union, Optional


class ButtonType(Enum):
    DIGIT = auto()
    OPERATOR = auto()
    FUNCTION = auto()

#電卓の計算ロジック
class Calculator:
    def __init__(self):
        self.memory: float = 0
        self.reset()
    
    #計算状態をリセット
    def reset(self) -> None:
        self.operator: str = "+"
        self.operand1: float = 0
        self.new_operand: bool = True

    #数値を適切な形式で文字列に変換
    @staticmethod
    def format_number(num: float) -> str:
        try:
            if math.isnan(num) or math.isinf(num):
                return "エラー"
            if abs(num) > 1e10:
                return f"{num:.2e}"
            return str(int(num) if num.is_integer() else round(num, 10))
        except Exception:
            return "エラー"
    
    #階乗を計算
    def calculate_factorial(self, n: float) -> str:
        try:
            if not float(n).is_integer():
                return "エラー: 整数のみ"
            n = int(n)
            if n < 0:
                return "エラー: 正の数のみ"
            if n > 170:
                return "エラー: 数が大きすぎます"
            result = math.factorial(n)
            return self.format_number(float(result))
        except Exception as e:
            return f"エラー: {str(e)}"

    #四則演算を計算
    def calculate(self, operand1: float, operand2: float, operator: str) -> str:
        try:
            result = {
                "+": lambda: operand1 + operand2,
                "-": lambda: operand1 - operand2,
                "×": lambda: operand1 * operand2,
                "÷": lambda: operand1 / operand2 if operand2 != 0 else float('inf')
            }[operator]()
            return self.format_number(result)
        except Exception:
            return "エラー"

    #平方根を計算
    def calculate_sqrt(self, value: float) -> str:
        try:
            if value < 0:
                return "エラー: 負の数の平方根"
            result = math.sqrt(value)
            return self.format_number(result)
        except Exception:
            return "エラー"
    
    #汎用関数計算メソッド
    def calculate_function(self, func: Callable[[float], float], value: float) -> str:
        try:
            result = func(value)
            return self.format_number(result)
        except ZeroDivisionError:
            return "エラー: ゼロ除算"
        except Exception:
            return "エラー"

#電卓のボタン
class CalcButton(ft.ElevatedButton):
    def __init__(self, text: str, btn_type: ButtonType, on_click: Callable, expand: int = 1):
        super().__init__()
        self.text = text
        self.expand = expand
        self.on_click = on_click
        self.data = text
        self.style = ft.ButtonStyle(
            padding=ft.padding.all(10),
            shape=ft.RoundedRectangleBorder(radius=5),
        )
        
        # ボタンサイズを統一
        self.width = 65
        self.height = 50
        
        # ボタンタイプに基づいてスタイルを設定
        styles = {
            ButtonType.DIGIT: (ft.colors.WHITE24, ft.colors.WHITE),
            ButtonType.OPERATOR: (ft.colors.ORANGE, ft.colors.WHITE),
            ButtonType.FUNCTION: (ft.colors.BLUE_GREY_100, ft.colors.BLACK)
        }
        self.bgcolor, self.color = styles[btn_type]

#計算機のUIコンポーネント
class CalculatorApp(ft.Container):
    def __init__(self):
        super().__init__()
        self.calculator = Calculator()
        self.setup_ui()
    
    def setup_ui(self):
        # ディスプレイの設定
        self.display = ft.Text(
            value="0",
            color=ft.colors.WHITE,
            size=32,  # フォントサイズを調整
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.RIGHT,
        )
        
        self.memory_display = ft.Text(
            value="M: 0",
            color=ft.colors.WHITE60,
            size=14,  # フォントサイズを調整
            visible=False
        )
        
        # コンテナの設定
        self.width = 320  # 幅を調整
        self.bgcolor = ft.colors.BLACK
        self.border_radius = ft.border_radius.all(10)
        self.padding = 20  # パディングを増やして余白を確保
        
        # ボタンレイアウトの定義
        button_rows = [
            [
                ("MC", ButtonType.FUNCTION),
                ("MR", ButtonType.FUNCTION),
                ("M+", ButtonType.FUNCTION),
                ("M-", ButtonType.FUNCTION),
            ],
            [
                ("AC", ButtonType.FUNCTION),
                ("+/-", ButtonType.FUNCTION),
                ("%", ButtonType.FUNCTION),
                ("n!", ButtonType.FUNCTION),
            ],
            [
                ("π", ButtonType.FUNCTION),
                ("√", ButtonType.FUNCTION),
                ("x²", ButtonType.FUNCTION),
                ("¹/x", ButtonType.FUNCTION),
            ],
            [
                ("7", ButtonType.DIGIT),
                ("8", ButtonType.DIGIT),
                ("9", ButtonType.DIGIT),
                ("÷", ButtonType.OPERATOR)
            ],
            [
                ("4", ButtonType.DIGIT),
                ("5", ButtonType.DIGIT),
                ("6", ButtonType.DIGIT),
                ("×", ButtonType.OPERATOR)
            ],
            [
                ("1", ButtonType.DIGIT),
                ("2", ButtonType.DIGIT),
                ("3", ButtonType.DIGIT),
                ("-", ButtonType.OPERATOR)
            ],
            [
                ("0", ButtonType.DIGIT),  # expandを削除
                (".", ButtonType.DIGIT),
                ("=", ButtonType.OPERATOR),
                ("+", ButtonType.OPERATOR)
            ]
        ]
        
        self.content = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            self.memory_display,
                            ft.Row(
                                controls=[self.display],
                                alignment=ft.MainAxisAlignment.END
                            )
                        ],
                        spacing=2
                    ),
                    margin=ft.margin.only(bottom=15),  # マージンを調整
                    padding=ft.padding.all(10),  # パディングを調整
                ),
                *[self.create_button_row(row) for row in button_rows]
            ],
            spacing=10  # 行間のスペースを調整
        )

    #ボタン行を作成
    def create_button_row(self, button_specs: list) -> ft.Row:
        return ft.Row(
            controls=[
                CalcButton(text, btn_type, self.button_clicked)  # expandパラメータを削除
                for text, btn_type, *_ in button_specs
            ],
            spacing=10  # ボタン間のスペースを調整
        )
    
    #メモリ操作を処理
    def handle_memory_operation(self, operation: str) -> None:
        try:
            current_value = float(self.display.value)
            
            operations = {
                "MC": lambda: self._clear_memory(),
                "MR": lambda: self._recall_memory(),
                "M+": lambda: self._add_to_memory(current_value),
                "M-": lambda: self._subtract_from_memory(current_value)
            }
            
            operations[operation]()
            self._update_memory_display()
            
        except Exception as e:
            self.display.value = f"エラー: {str(e)}"
            
        self.update()
    
    #メモリをクリア
    def _clear_memory(self) -> None:
        self.calculator.memory = 0
        self.memory_display.visible = False
    
    #メモリから値を呼び出し
    def _recall_memory(self) -> None:
        self.display.value = self.calculator.format_number(self.calculator.memory)
        self.calculator.new_operand = False
    
    #メモリに値を加算
    def _add_to_memory(self, value: float) -> None:
        self.calculator.memory += value
        self.memory_display.visible = True
    
    #メモリから値を減算
    def _subtract_from_memory(self, value: float) -> None:
        self.calculator.memory -= value
        self.memory_display.visible = True
    
    #メモリ表示を更新
    def _update_memory_display(self) -> None:
        if self.memory_display.visible:
            self.memory_display.value = f"M: {self.calculator.format_number(self.calculator.memory)}"

    #ボタンクリックイベントを処理
    def button_clicked(self, e: ft.ControlEvent) -> None:
        data = e.control.data
        
        try:
            if data in ["MC", "MR", "M+", "M-"]:
                self.handle_memory_operation(data)
                return
                
            if self.display.value.startswith("エラー") or data == "AC":
                self._handle_clear()
            elif data == "n!":
                self._handle_factorial()
            elif data == "√":
                self._handle_sqrt()
            elif data == "π":
                self._handle_pi()
            elif data == "x²":
                self._handle_square()
            elif data == "¹/x":
                self._handle_reciprocal()
            elif data in "0123456789.":
                self._handle_digit(data)
            elif data in "+-×÷":
                self._handle_operator(data)
            elif data == "=":
                self._handle_equals()
            elif data == "%":
                self._handle_percentage()
            elif data == "+/-":
                self._handle_sign_change()
                
            self.update()
                
        except Exception as e:
            self.display.value = f"エラー: {str(e)}"
            self.update()
    
    #クリア処理
    def _handle_clear(self) -> None:
        self.display.value = "0"
        self.calculator.reset()
    
    #階乗処理
    def _handle_factorial(self) -> None:
        value = float(self.display.value)
        self.display.value = self.calculator.calculate_factorial(value)
        self.calculator.new_operand = True
    
    #平方根処理
    def _handle_sqrt(self) -> None:
        self.display.value = self.calculator.calculate_sqrt(float(self.display.value))
        self.calculator.new_operand = True
    
    #円周率処理
    def _handle_pi(self) -> None:
        self.display.value = self.calculator.format_number(math.pi)
        self.calculator.new_operand = False
    
    #二乗処理
    def _handle_square(self) -> None:
        value = float(self.display.value)
        self.display.value = self.calculator.calculate_function(lambda x: x * x, value)
        self.calculator.new_operand = True
    
    #逆数処理
    def _handle_reciprocal(self) -> None:
        value = float(self.display.value)
        self.display.value = self.calculator.calculate_function(lambda x: 1 / x, value)
        self.calculator.new_operand = True
    
    #数字入力処理
    def _handle_digit(self, digit: str) -> None:
        if self.calculator.new_operand:
            self.display.value = digit
            self.calculator.new_operand = False
        else:
            if digit == "." and "." in self.display.value:
                return
            self.display.value += digit
    
    #演算子処理
    def _handle_operator(self, operator: str) -> None:
        self.display.value = self.calculator.calculate(
            self.calculator.operand1,
            float(self.display.value),
            self.calculator.operator
        )
        self.calculator.operator = operator
        if not self.display.value.startswith("エラー"):
            self.calculator.operand1 = float(self.display.value)
        self.calculator.new_operand = True
    
    #イコール処理
    def _handle_equals(self) -> None:
        self.display.value = self.calculator.calculate(
            self.calculator.operand1,
            float(self.display.value),
            self.calculator.operator
        )
        self.calculator.reset()
    
    #パーセント処理
    def _handle_percentage(self) -> None:
        value = float(self.display.value)
        self.display.value = self.calculator.calculate_function(lambda x: x / 100, value)
        self.calculator.new_operand = True
    
    #符号反転処理
    def _handle_sign_change(self) -> None:
        value = float(self.display.value)
        self.display.value = self.calculator.format_number(-value if value != 0 else 0)


def main(page: ft.Page):
    page.title = "電卓"
    page.theme_mode = ft.ThemeMode.DARK
    calc = CalculatorApp()
    page.add(calc)


if __name__ == "__main__":
    ft.app(target=main)