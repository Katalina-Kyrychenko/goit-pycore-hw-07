# bot.py
from __future__ import annotations
from collections import UserDict
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple, Dict, Callable
import re


# =========================
# 1) Модельні класи
# =========================

class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self) -> str:
        return str(self.value)


class Name(Field):
    pass


class Phone(Field):
    """Телефон рівно з 10 цифр."""
    def __init__(self, value: str):
        digits = re.sub(r"\D", "", value or "")
        if len(digits) != 10:
            raise ValueError("Phone must contain exactly 10 digits")
        super().__init__(digits)


class Birthday(Field):
    """Дата народження у форматі DD.MM.YYYY"""
    def __init__(self, value: str):
        try:
            dt = datetime.strptime(value, "%d.%m.%Y").date()
            super().__init__(dt)
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")


class Record:
    def __init__(self, name: str):
        self.name = Name(name)
        self.phones: List[Phone] = []
        self.birthday: Optional[Birthday] = None

    def add_phone(self, phone: str) -> None:
        self.phones.append(Phone(phone))

    def change_phone(self, old_phone: str, new_phone: str) -> bool:
        old_digits = re.sub(r"\D", "", old_phone or "")
        for i, p in enumerate(self.phones):
            if p.value == old_digits:
                self.phones[i] = Phone(new_phone)
                return True
        return False

    def add_birthday(self, birthday_str: str) -> None:
        self.birthday = Birthday(birthday_str)

    def phones_str(self) -> str:
        return ", ".join(p.value for p in self.phones) if self.phones else "—"

    def __str__(self):
        b = self.birthday.value.strftime("%d.%m.%Y") if self.birthday else "—"
        return f"{self.name.value}: {self.phones_str()} | birthday: {b}"


class AddressBook(UserDict):
    def add_record(self, record: Record) -> None:
        self.data[record.name.value] = record

    def find(self, name: str) -> Optional[Record]:
        return self.data.get(name)

    def get_upcoming_birthdays(self, today: Optional[date] = None) -> Dict[str, List[str]]:
        if today is None:
            today = date.today()

        per_day: Dict[str, List[str]] = {}

        def add(name: str, d: date):
            weekday = d.strftime("%A")
            per_day.setdefault(weekday, []).append(name)

        end = today + timedelta(days=7)
        for rec in self.data.values():
            if not rec.birthday:
                continue

            bday = rec.birthday.value
            bday_this_year = date(today.year, bday.month, bday.day)
            if bday_this_year < today:
                bday_this_year = date(today.year + 1, bday.month, bday.day)

            if today <= bday_this_year < end:
                congr_date = bday_this_year
                if congr_date.weekday() == 5:
                    congr_date += timedelta(days=2)
                elif congr_date.weekday() == 6:
                    congr_date += timedelta(days=1)

                add(rec.name.value, congr_date)

        for k in list(per_day.keys()):
            per_day[k].sort(key=lambda s: s.lower())
        return per_day


# =========================
# 2) Інфраструктура CLI
# =========================

def input_error(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except IndexError:
            return "Not enough arguments."
        except KeyError as e:
            return f"Contact not found: {e}"
        except ValueError as e:
            return str(e)
    return wrapper


def parse_input(user_input: str) -> Tuple[str, List[str]]:
    parts = user_input.strip().split()
    if not parts:
        return "", []
    command = parts[0].lower()
    args = parts[1:]
    return command, args


# =========================
# 3) Обробники команд
# =========================

@input_error
def add_contact(args: List[str], book: AddressBook) -> str:
    name, phone, *_ = args
    record = book.find(name)
    msg = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        msg = "Contact added."
    if phone:
        record.add_phone(phone)
    return msg


@input_error
def change_contact(args: List[str], book: AddressBook) -> str:
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    if record is None:
        return "Contact not found."
    if record.change_phone(old_phone, new_phone):
        return "Phone updated."
    return "Old phone not found for this contact."


@input_error
def show_phones(args: List[str], book: AddressBook) -> str:
    name, *_ = args
    record = book.find(name)
    if record is None:
        return "Contact not found."
    return record.phones_str()


@input_error
def show_all(args: List[str], book: AddressBook) -> str:
    if not book.data:
        return "Address book is empty."
    lines = [str(rec) for rec in book.values()]
    return "\n".join(lines)


@input_error
def add_birthday(args: List[str], book: AddressBook) -> str:
    name, birthday_str, *_ = args
    record = book.find(name)
    if record is None:
        record = Record(name)
        book.add_record(record)
    record.add_birthday(birthday_str)
    return "Birthday set."


@input_error
def show_birthday(args: List[str], book: AddressBook) -> str:
    name, *_ = args
    record = book.find(name)
    if record is None:
        return "Contact not found."
    if not record.birthday:
        return "Birthday is not set."
    return record.birthday.value.strftime("%d.%m.%Y")


@input_error
def birthdays(args: List[str], book: AddressBook) -> str:
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No birthdays in the next 7 days."
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    lines = []
    for day in order:
        if day in upcoming:
            names = ", ".join(upcoming[day])
            lines.append(f"{day}: {names}")
    return "\n".join(lines)


def show_help() -> str:
    """Выводит все доступные команды"""
    commands = {
        "add [ім'я] [телефон]": "Додати новий контакт або телефон до існуючого.",
        "change [ім'я] [старий] [новий]": "Змінити номер телефону для контакту.",
        "phone [ім'я]": "Показати телефони контакту.",
        "all": "Показати всі контакти.",
        "add-birthday [ім'я] [дата]": "Додати дату народження (DD.MM.YYYY).",
        "show-birthday [ім'я]": "Показати дату народження.",
        "birthdays": "Показати, кого привітати на наступному тижні.",
        "hello": "Привітатися з ботом.",
        "help": "Показати цей список команд.",
        "close / exit": "Вийти з програми.",
    }
    return "\n".join(f"{cmd}: {desc}" for cmd, desc in commands.items())


# =========================
# 4) Головний цикл
# =========================

def main():
    book = AddressBook()
    print("Welcome to the assistant bot!")
    print("Type 'help' to see available commands.")
    while True:
        user_input = input("Enter a command: ")
        command, args = parse_input(user_input)

        if command in ("close", "exit"):
            print("Good bye!")
            break

        elif command == "hello":
            print("How can I help you?")

        elif command == "help":
            print(show_help())

        elif command == "add":
            print(add_contact(args, book))

        elif command == "change":
            print(change_contact(args, book))

        elif command == "phone":
            print(show_phones(args, book))

        elif command == "all":
            print(show_all(args, book))

        elif command == "add-birthday":
            print(add_birthday(args, book))

        elif command == "show-birthday":
            print(show_birthday(args, book))

        elif command == "birthdays":
            print(birthdays(args, book))

        else:
            print("Invalid command. Type 'help' to see all commands.")


if __name__ == "__main__":
    main()
