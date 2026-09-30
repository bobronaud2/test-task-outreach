from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from outreach.personalize import read_rows

HEADERS = {
    "company": "Компания",
    "website": "Сайт",
    "contact_name": "Имя ЛПР",
    "contact_title": "Должность",
    "email": "Email",
    "email_type": "Тип email",
    "email_source_url": "Где найден email",
    "contact_source_url": "Где найден ЛПР",
    "sales_signal": "Признак активных продаж",
    "city": "Город",
    "segment": "Сегмент",
    "personalization": "Персонализация",
    "personalization_source": "Источник персонализации",
    "site_company": "Компания по данным сайта",
    "status": "Статус",
    "issues": "Проблемы",
    "step": "Письмо",
    "delay_days": "Через сколько дней",
    "subject": "Тема",
    "body": "Текст",
}
WIDE_COLUMNS = {"personalization", "issues", "body", "sales_signal"}


def add_sheet(book: Workbook, title: str, rows: list[dict]) -> None:
    sheet = book.create_sheet(title)
    fields = list(rows[0])
    sheet.append([HEADERS.get(field, field) for field in fields])
    for row in rows:
        sheet.append([row.get(field, "") for field in fields])

    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for index, field in enumerate(fields, start=1):
        letter = sheet.cell(row=1, column=index).column_letter
        sheet.column_dimensions[letter].width = 60 if field in WIDE_COLUMNS else 22
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    sheet.freeze_panes = "A2"


def export_workbook(sheets: dict[str, Path], target: Path) -> None:
    book = Workbook()
    book.remove(book.active)
    for title, source in sheets.items():
        add_sheet(book, title, read_rows(source))
    book.save(target)
