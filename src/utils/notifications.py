#импорт компонентов библиотек
import random
import tkinter as tk
from tkinter import messagebox
from src.utils.cache import CacheManager
from src.api.openrouter import validate_api_key, fetch_balance

class AuthWindow(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.create_widgets()
        self.pack(fill=tk.BOTH, expand=True)
    
    def create_widgets(self):
        #ввод PIN-кода или API-ключа
        tk.Label(self, text="PIN-код или API-key").pack(padx=10, pady=10)
        self.entry_pin_or_key = tk.Entry(self, show="*")  # Скрытый ввод символов
        self.entry_pin_or_key.pack(padx=10, pady=10)
        
        #кнопка подтверждения
        tk.Button(self, text="Войти", command=self.on_authenticate).pack(padx=10, pady=10)
        
        #кнопка сброса ключа
        tk.Button(self, text="Сбросить ключ", command=self.on_reset_key).pack(padx=10, pady=10)
    
    def on_authenticate(self):
        input_value = self.entry_pin_or_key.get().strip()
        
        #получаем кэшированный ключ и PIN
        cached_data = CacheManager.load_cache()
        
        if len(input_value) == 4 and cached_data['pin'] == input_value:
            #вход выполнен успешно по PIN
            self.master.switch_to_main()  #переключаемся на главное окно
        elif len(input_value) > 4:
            #проверяем валидность API-ключа
            is_valid, balance = validate_api_key(input_value)
            if is_valid and balance > 0:
                #генерируем случайный PIN и сохраняем ключ + PIN
                new_pin = ''.join(str(random.randrange(10)) for _ in range(4))
                CacheManager.save_cache({'api_key': input_value, 'pin': new_pin})
                self.master.switch_to_main()  #успешный вход
            else:
                messagebox.showerror("Ошибка", "Некорректный API-ключи или недостаточный баланс.")
        else:
            messagebox.showwarning("Внимание", "Неверный формат PIN или API-ключи.")
    
    def on_reset_key(self):
        #удаляем старый ключ и PIN
        CacheManager.clear_cache()
        messagebox.showinfo("Уведомление", "Ключ успешно удалён.")
        self.entry_pin_or_key.delete(0, tk.END)