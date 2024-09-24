import json
import os
import telebot
from telebot import types

class ATM:
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username
        self.load_data()

    def load_data(self):
        if os.path.exists('database.json'):
            with open('database.json', 'r') as file:
                self.master_data = json.load(file)
        else:
            self.master_data = {}

        user_data = self.master_data.get(str(self.user_id), {})
        self.username = user_data.get('username', None)
        self.balance = user_data.get('balance', 0)
        self.expenses = user_data.get('expenses', 0)
        self.income_sources = user_data.get('income_sources', [])
        self.income = user_data.get('income', {})
        self.password = user_data.get('password', '')

    def save_data(self):
        self.master_data[str(self.user_id)] = {
            'username': self.username,
            'balance': self.balance,
            'expenses': self.expenses,
            'income_sources': self.income_sources,
            'income': self.income,
            'password': self.password
        }
        with open('database.json', 'w') as file:
            json.dump(self.master_data, file, indent=4)

    def register(self, username, password):
        if str(self.user_id) in self.master_data:
            existing_user = self.master_data[str(self.user_id)]
            return (f"You are already registered.\n"
                    f"DATA USER:\n"
                    f"username: {existing_user['username']}\n"
                    f"password: {existing_user.get('password', 'Not set')}")
        
        self.username = username
        self.password = password
        self.save_data()
        return f"Registration successful!\n\nDATA USER:\nusername: {self.username}\npassword: {self.password}"

    def add_income_source(self, source):
        if source not in self.income_sources:
            self.income_sources.append(source)
            self.save_data()
            return f"Added income source: {source}."
        else:
            return "Income source already exists."

    def deposit(self, amount, source):
        self.balance += amount
        if source in self.income:
            self.income[source] += amount
        else:
            self.income[source] = amount
        self.save_data()
        return f"Deposited: {amount} from {source}. New balance: {self.balance}"

    def withdraw(self, amount, reason):
        if amount <= self.balance:
            self.balance -= amount
            self.expenses += amount
            self.save_data()
            return f"Withdrawn: {amount} for {reason}. New balance: {self.balance}"
        else:
            return "Insufficient funds."

    def status(self):
        income_summary = "\n".join([f" - {source}: {amount}" for source, amount in self.income.items()])
        return (f"Balance: {self.balance}\n"
                f"Total Income: {sum(self.income.values())}\n"
                f"Total Expenses: {self.expenses}\n"
                f"Income Sources:\n{income_summary}")

    def print_all_data(self):
        return f"Data for {self.username}:\n" \
               f"Balance: {self.balance}\n" \
               f"Expenses: {self.expenses}\n" \
               f"Income: {json.dumps(self.income, indent=4)}\n"

def read_token():
    with open('token_bot.txt', 'r') as file:
        return file.read().strip()

API_TOKEN = read_token()
bot = telebot.TeleBot(API_TOKEN)

# Password yang benar
PASSWORD = "nikotin123"

# Fungsi untuk mengirimkan database.json
@bot.message_handler(commands=['database'])
def send_welcome(message):
    bot.reply_to(message, "Masukkan password untuk mengakses database:")

@bot.message_handler(func=lambda message: True)
def check_password(message):
    if message.text == PASSWORD:
        # Cek apakah file database.json ada
        if os.path.exists('database.json'):
            with open('database.json', 'rb') as db_file:
                bot.send_document(message.chat.id, db_file)
        else:
            bot.reply_to(message, "File database.json tidak ditemukan.")
    else:
        bot.reply_to(message, "Password salah. Silakan coba lagi.")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Welcome to ATM Bot! Use /data to register income sources, /deposit, /withdraw, /status, /webview, or /printdata.")

@bot.message_handler(commands=['webview'])
def handle_registration(message):
    bot.send_message(message.chat.id, "Please enter your desired username:")
    bot.register_next_step_handler(message, process_username)

def process_username(message):
    username = message.text.strip()
    bot.send_message(message.chat.id, "Please enter your password:")
    bot.register_next_step_handler(message, lambda msg: process_password(msg, username))

def process_password(message, username):
    password = message.text.strip()
    atm = ATM(message.from_user.id, username)
    response = atm.register(username, password)
    bot.reply_to(message, response)

@bot.message_handler(commands=['data'])
def handle_data(message):
    bot.send_message(message.chat.id, "Enter a new income source (e.g., 'Bank Jateng').")
    bot.register_next_step_handler(message, process_new_income_source)

def process_new_income_source(message):
    atm = ATM(message.from_user.id, message.from_user.username)
    source = message.text.strip()
    response = atm.add_income_source(source)
    bot.reply_to(message, response)

@bot.message_handler(commands=['deposit'])
def handle_deposit(message):
    atm = ATM(message.from_user.id, message.from_user.username)
    keyboard = types.InlineKeyboardMarkup()
    
    for source in atm.income_sources:
        keyboard.add(types.InlineKeyboardButton(text=f"Deposit to {source}", callback_data=f"deposit_{source}"))

    keyboard.add(types.InlineKeyboardButton(text="Create New Income Source", callback_data="new_income_source"))
    bot.send_message(message.chat.id, "Choose an income source to deposit to:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("deposit_"))
def process_deposit(call):
    source = call.data.split("_")[1]
    bot.send_message(call.message.chat.id, f"Enter amount to deposit to {source}.")
    bot.register_next_step_handler(call.message, lambda m: deposit_amount(m, source))

def deposit_amount(message, source):
    atm = ATM(message.from_user.id, message.from_user.username)
    try:
        amount = float(message.text)
        response = atm.deposit(amount, source)
        bot.reply_to(message, response)
    except ValueError:
        bot.reply_to(message, "Invalid input. Please enter a valid amount.")

@bot.callback_query_handler(func=lambda call: call.data == "new_income_source")
def prompt_new_income_source(call):
    bot.send_message(call.message.chat.id, "Enter a new income source (e.g., 'Bank Jateng').")
    bot.register_next_step_handler(call.message, process_new_income_source)

@bot.message_handler(commands=['withdraw'])
def handle_withdraw(message):
    atm = ATM(message.from_user.id, message.from_user.username)
    keyboard = types.InlineKeyboardMarkup()
    
    for source in atm.income_sources:
        keyboard.add(types.InlineKeyboardButton(text=f"Withdraw from {source}", callback_data=f"withdraw_{source}"))

    keyboard.add(types.InlineKeyboardButton(text="Create New Income Source", callback_data="new_income_source"))
    bot.send_message(message.chat.id, "Choose an income source to withdraw from:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("withdraw_"))
def process_withdraw(call):
    source = call.data.split("_")[1]
    bot.send_message(call.message.chat.id, f"Enter amount to withdraw from {source}.")
    bot.register_next_step_handler(call.message, lambda m: withdraw_amount(m, source))

def withdraw_amount(message, source):
    atm = ATM(message.from_user.id, message.from_user.username)
    try:
        amount, reason = message.text.split(maxsplit=1)
        amount = float(amount)
        response = atm.withdraw(amount, reason)
        bot.reply_to(message, response)
    except ValueError:
        bot.reply_to(message, "Invalid input. Please use format: <amount> <reason>.")

@bot.message_handler(commands=['status'])
def handle_status(message):
    atm = ATM(message.from_user.id, message.from_user.username)
    response = atm.status()
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['printdata'])
def handle_print_data(message):
    atm = ATM(message.from_user.id, message.from_user.username)
    response = atm.print_all_data()
    bot.send_message(message.chat.id, response)

bot.polling()
