from datetime import date, datetime
from typing import List, Union

from flask import Markup, url_for

from .models import Expense, Mortgage, Property


def display_date(the_date: Union[date, datetime]) -> str:
    """Formats dates according to the US convention."""
    if type(the_date) is date or type(the_date) is datetime:
        return the_date.strftime("%m/%d/%Y")


def display_dollars(dollars: float) -> str:
    """Formats a number as US dollars."""
    if type(dollars) is float:
        return f"${dollars:,.0f}"


def display_percent(percent: Union[float, int]) -> str:
    """Displays a percentage with pretty formatting."""
    return f"{percent:.3f}%" if percent % 1 > 0 else f"{percent:.0f}%"


def display_table(data):
    """Display a dictionary as an html table."""
    table = "<table>\n"
    for key, value in data.items():
        table += f"<tr><th>{key}</th><td>{display_dollars(value)}</td></tr>\n"
    table += "</table>\n"
    return Markup(table)


def link_to_email(email: str) -> Markup:
    """Turn email addresses into hyperlinks."""
    return Markup(f'<a href="mailto:{email}">{email}</a>')


def link_to_expense(expense: Expense) -> Markup:
    """Display a link to an expenses show page."""
    if type(expense) is Expense:
        html = f'<a href="{url_for("ExpenseView.show", pk=expense.id)}">'
        html += f'<i class="fa fa-search"></i> {expense}</a>'
        return Markup(html)


def link_to_mortgage(mortgage: Mortgage) -> Markup:
    """Display a link to a mortgage's show page."""
    if type(mortgage) is Mortgage:
        html = f'<a href="{url_for("MortgageView.show", pk=mortgage.id)}">'
        html += f'<i class="fa fa-search"></i> {mortgage}</a>'
        return Markup(html)


def link_to_property(property: Property) -> Markup:
    """Display a link to a property's show page."""
    if type(property) is Property:
        html = f'<a href="{url_for("PropertyView.show", pk=property.id)}">'
        html += f'<i class="fa fa-search"></i> {property}</a>'
        return Markup(html)


def unordered_property_list(properties: List[Property]) -> Markup:
    """Display a list of properties as an html unordered list with links to their show pages."""
    html = "<ul>"
    for property in properties:
        html += f"<li>{link_to_property(property)}</li>"
    html += "</ul>"
    return Markup(html)
