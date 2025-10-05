"""
Основные компоненты Flet-приложения
"""

# Импорт необходимых библиотек и модулей
import flet as ft                  # Фреймворк для создания пользовательского интерфейса
from ui.styles import AppStyles    # Импорт стилей приложения (будет рассмотрен в следующей части урока)
import asyncio                     # Библиотека для асинхронного программирования
import random
import string
import aiohttp
from utils.cache import CacheManager

class MessageBubble(ft.Container):
    """
    Компонент "пузырька" сообщения в чате.
    
    Наследуется от ft.Container для создания стилизованного контейнера сообщения.
    Отображает сообщения пользователя и AI с разными стилями и позиционированием.
    
    Args:
        message (str): Текст сообщения для отображения
        is_user (bool): Флаг, указывающий, является ли это сообщением пользователя
    """
    def __init__(self, message: str, is_user: bool):
        # Инициализация родительского класса Container
        super().__init__()
        
        # Настройка отступов внутри пузырька
        self.padding = 10
        
        # Настройка скругления углов пузырька
        self.border_radius = 10
        
        # Установка цвета фона в зависимости от отправителя:
        # - Синий для сообщений пользователя
        # - Серый для сообщений AI
        self.bgcolor = ft.Colors.BLUE_700 if is_user else ft.Colors.GREY_700
        
        # Установка выравнивания пузырька:
        # - Справа для сообщений пользователя
        # - Слева для сообщений AI
        self.alignment = ft.alignment.center_right if is_user else ft.alignment.center_left
        
        # Настройка внешних отступов для создания эффекта диалога:
        # - Отступ слева для сообщений пользователя
        # - Отступ справа для сообщений AI
        # - Небольшие отступы сверху и снизу для разделения сообщений
        self.margin = ft.margin.only(
            left=50 if is_user else 0,      # Отступ слева
            right=0 if is_user else 50,      # Отступ справа
            top=5,                           # Отступ сверху
            bottom=5                         # Отступ снизу
        )
        
        # Создание содержимого пузырька
        self.content = ft.Column(
            controls=[
                # Текст сообщения с настройками отображения
                ft.Text(
                    value=message,                    # Текст сообщения
                    color=ft.Colors.WHITE,            # Белый цвет текста
                    size=16,                         # Размер шрифта
                    selectable=True,                 # Возможность выделения текста
                    weight=ft.FontWeight.W_400       # Нормальная толщина шрифта
                )
            ],
            tight=True  # Плотное расположение элементов в колонке
        )


class ModelSelector(ft.Dropdown):
    """
    Выпадающий список для выбора AI модели с функцией поиска.
    
    Наследуется от ft.Dropdown для создания кастомного выпадающего списка
    с дополнительным полем поиска для фильтрации моделей.
    
    Args:
        models (list): Список доступных моделей в формате:
                      [{"id": "model-id", "name": "Model Name"}, ...]
    """
    def __init__(self, models: list):
        # Инициализация родительского класса Dropdown
        super().__init__()
        
        # Применение стилей из конфигурации к компоненту
        for key, value in AppStyles.MODEL_DROPDOWN.items():
            setattr(self, key, value)
            
        # Настройка внешнего вида выпадающего списка
        self.label = None                    # Убираем текстовую метку
        self.hint_text = "Выбор модели"      # Текст-подсказка
        
        # Создание списка опций из предоставленных моделей
        self.options = [
            ft.dropdown.Option(
                key=model['id'],             # ID модели как ключ
                text=model['name']           # Название модели как отображаемый текст
            ) for model in models
        ]
        
        # Сохранение полного списка опций для фильтрации
        self.all_options = self.options.copy()
        
        # Установка начального значения (первая модель из списка)
        self.value = models[0]['id'] if models else None
        
        # Создание поля поиска для фильтрации моделей
        self.search_field = ft.TextField(
            on_change=self.filter_options,        # Функция обработки изменений
            hint_text="Поиск модели",            # Текст-подсказка в поле поиска
            **AppStyles.MODEL_SEARCH_FIELD       # Применение стилей из конфигурации
        )

    def filter_options(self, e):
        """
        Фильтрация списка моделей на основе введенного текста поиска.
        
        Args:
            e: Событие изменения текста в поле поиска
        """
        # Получение текста поиска в нижнем регистре
        search_text = self.search_field.value.lower() if self.search_field.value else ""
        
        # Если поле поиска пустое - показываем все модели
        if not search_text:
            self.options = self.all_options
        else:
            # Фильтрация моделей по тексту поиска
            # Ищем совпадения в названии или ID модели
            self.options = [
                opt for opt in self.all_options
                if search_text in opt.text.lower() or search_text in opt.key.lower()
            ]
        
        # Обновление интерфейса для отображения отфильтрованного списка
        e.page.update()

class RegistrationComponent(ft.UserControl):
    def __init__(self, page, register_callback):
        super().__init__()
        self.page = page
        self.register_callback = register_callback
        self.input_field = ft.TextField(label="API Key")
        self.submit_btn = ft.ElevatedButton(text="Зарегистрироваться", on_click=self.on_register)
    
    def build(self):
        return ft.Column([
            self.input_field,
            self.submit_btn
        ])
    
    async def on_register(self, event):
        """
        Обработчик события нажатия кнопки "Зарегистрироваться".
        """
        api_key = self.input_field.value.strip()
        is_valid, balance = await self.validate_api_key(api_key)
        if is_valid:
            pin_code = ''.join(random.choice(string.digits) for _ in range(4))
            CacheManager().update_auth_data(api_key=api_key, pin=pin_code)
            self.register_callback(self.page, pin_code)  # Передача page и pin_code

            # Уведомление с PIN-кодом
            snack_bar = ft.SnackBar(
                content=ft.Text(f"ПИН-код успешно создан: {pin_code}"),
                action="Закрыть",
                open=True
            )
            self.page.snack_bar = snack_bar
            self.page.update()

            # Используем FutureTimer для задания таймера
            await asyncio.sleep(2)  # Ждем 2 секунды
            snack_bar.open = False   # Устанавливаем состояние SnackBar в закрытое
            self.page.update()       # Обновляем страницу
        else:
            # Для случая некорректного ключа оставляем вывод без автоскрытия
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Некорректный API ключ или недостаточно средств."))
            self.page.snack_bar.open = True
            self.page.update()
    
    async def validate_api_key(self, api_key):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get('https://openrouter.ai/api/v1/balance') as resp:
                # Печатаем полный ответ от сервера
                print(await resp.text())
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        return True, data.get('balance', '$100.00')
                    except aiohttp.client_exceptions.ContentTypeError:
                        return True, "$100.00"
                else:
                    return False, f"Ошибка при проверке API ({resp.status})"

class LoginComponent(ft.UserControl):
    def __init__(self, page, login_callback):
        super().__init__()
        self.page = page
        self.login_callback = login_callback
        self.input_field = ft.TextField(label="PIN-код")
        self.submit_btn = ft.ElevatedButton(text="Войти", on_click=self.on_login)
        self.reset_btn = ft.TextButton(text="Сбросить ключ", on_click=self.on_reset)
    
    def build(self):
        return ft.Column([
            self.input_field,
            ft.Row([self.submit_btn, self.reset_btn])
        ])
    
    async def on_login(self, event):
        entered_pin = self.input_field.value.strip()
        _, stored_pin = CacheManager().get_auth_data()
        if entered_pin == stored_pin:
            # Очистка существующей страницы перед созданием нового окна (если пин-код верный)
            self.page.clean()
            main_window = MainWindow(self.page)
            self.page.add(main_window)
            self.page.update()
        else:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Неверный PIN-код."))
            self.page.snack_bar.open = True
            self.page.update()
    
    async def on_reset(self, event):
        CacheManager().clear_auth_data()
        self.page.clean()
        registration_component = RegistrationComponent(self.page, register_callback=register_and_open_main)
        self.page.add(registration_component)
        self.page.update()

def register_and_open_main(page, pin_code):
    """
    Callback после успешной регистрации API-ключа.
    """
    # Очистка предыдущей страницы
    page.clean()
    # Открытие основного окна
    main_window = MainWindow(page)
    page.add(main_window)
    page.update()

class MainWindow(ft.UserControl):
    """
    Основное окно приложения после успешного входа.
    """
    def __init__(self, page):
        super().__init__()
        self.page = page
    
    def build(self):
        return ft.Column([
            ft.Text("Добро пожаловать!",
                   style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            ft.Text("Ваш сеанс начался.", expand=True),
            ft.Text("Пожалуйста, закройте это окно. Автоматическое закрытие не работает.",
                   style=ft.TextThemeStyle.TITLE_SMALL)
        ], alignment=ft.MainAxisAlignment.CENTER)