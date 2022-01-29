from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List, Union
from flask import flash, Markup, redirect, render_template, session, url_for
from flask_appbuilder import (
    AppBuilder,
    BaseView,
    ModelView,
    SimpleFormView,
)
from flask_appbuilder.actions import action
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.views import CompactCRUDMixin
from flask_mail import Message
from mortgage import Loan

from app import mail
from . import appbuilder, db
from .forms import EmailForm
from .models import Booking, Contact, Expense, Income, Inventory, Mortgage, Property
from .utils import (
    display_date,
    display_dollars,
    display_percent,
    display_table,
    link_to_email,
    link_to_expense,
    link_to_mortgage,
    link_to_property,
    unordered_property_list,
)


class BookingView(ModelView, CompactCRUDMixin):
    """Provides add, edit, and show support for bookings."""

    datamodel = SQLAInterface(Booking)
    list_title = "Bookings"


class ContactView(ModelView, CompactCRUDMixin):
    """Provides add, edit, list, and show support for contacts."""

    datamodel = SQLAInterface(Contact)
    base_order = ("last_name", "asc")
    formatters_columns = {
        "email": link_to_email,
        "expense": link_to_expense,
        "properties": unordered_property_list,
    }
    label_columns = {"full_name": "Name"}
    list_columns = ["full_name", "company", "role", "email", "phone"]
    list_title = "Contacts"

    @action("email", "Email", icon="fa-envelope")
    def email(self, contacts: Union[Contact, List[Contact]]) -> Markup:
        """Send an email to one or more contacts."""
        session["contacts"] = []
        if type(contacts) == list:
            for contact in contacts:
                session["contacts"].append(contact.id)
        else:
            session["contacts"].append(contacts.id)
        return redirect(
            url_for("ContactEmailFormView.this_form_get", contacts=session["contacts"])
        )


class ContactEmailFormView(SimpleFormView):
    """Displays the form for sending emails to contacts."""

    form = EmailForm
    form_title = "Email Contacts"
    message = "Email sent."

    def form_post(self, form):
        """Process the results of the email form."""
        contacts = session.pop("contacts")
        with mail.connect() as conn:
            for id in contacts:
                contact = db.session.query(Contact).filter_by(id=id).one()
                msg = Message(
                    sender=("Property Manager App", "thomas.stivers@gmail.com"),
                    recipients=[(contact.full_name, contact.email)],
                )
                msg.subject = form.subject.data.format(contact=contact)
                msg.html = form.body.data.format(contact=contact)
                conn.send(msg)
                flash(f"Email sent to {contact.full_name}.", "info")


class FinanceViewBase(ModelView, CompactCRUDMixin):
    """Base configuration used by both ExpenseView and IncomeView classes."""

    add_exclude_columns = edit_exclude_columns = [
        "changed_by",
        "changed_on",
        "created_by",
        "created_on",
    ]
    formatters_columns = {
        "amount": display_dollars,
        "date": display_date,
        "description": Markup,
        "property": link_to_property,
        "tax": display_dollars,
    }


class ExpenseView(FinanceViewBase):
    """Provides add, edit, list, and show pages for expenses."""

    datamodel = SQLAInterface(Expense)
    base_order = ("date", "desc")
    label_columns = {"receipt_link": "Receipt"}
    list_columns = ["payee", "amount", "tax", "date", "property", "receipt_link"]
    list_title = "Expenses"
    show_columns = [
        "property",
        "amount",
        "tax",
        "payee",
        "description",
        "date",
        "tax_deduction",
        "receipt_link",
    ]


class IncomeView(FinanceViewBase):
    """Provides add, edit, list, and show pages for income sources."""

    datamodel = SQLAInterface(Income)
    list_columns = ["amount", "payer", "date", "property"]
    list_title = "Income"


class InventoryView(ModelView, CompactCRUDMixin):
    """Configures the add, edit, list, and show pages for Inventory items."""

    datamodel = SQLAInterface(Inventory)
    add_exclude_columns = edit_exclude_columns = show_exclude_columns = [
        "changed_by",
        "changed_on",
        "created_by",
        "created_on",
    ]
    add_title = "Add Inventory Item"
    edit_title = "Edit Inventory Item"
    formatters_columns = {
        "calculated_sales_tax": display_dollars,
        "cost": display_dollars,
        "property": link_to_property,
        "purchase_date": display_date,
        "sales_tax": display_dollars,
        "total_cost": display_dollars,
    }
    label_columns = {"calculated_sales_tax": "Sales Tax"}
    list_columns = [
        "item",
        "total_cost",
        "quantity",
        "purchase_date",
        "category",
        "property",
    ]
    list_title = "Inventory"
    show_title = "Show Inventory Item"


class MortgageView(ModelView, CompactCRUDMixin):
    """Configures the add, edit, list, and show views on the Mortgage class."""

    datamodel = SQLAInterface(Mortgage)
    add_exclude_columns = edit_exclude_columns = [
        "changed_by",
        "changed_on",
        "created_by",
        "created_on",
    ]
    description_columns = {
        "term": "Term of the loan in years",
        "rate": "The annual interest rate",
        "down_payment": "The down payment as a percentage of the property value",
    }
    label_columns = {
        "term": "Term (years)",
        "closing": "Closing Costs",
        "has_insurance": "Includes Insurance",
        "has_PMI": "Includes PMI",
        "has_tax": "Includes Property Tax",
    }
    list_columns = [
        "amount",
        "rate",
        "term",
        "down_payment",
        "monthly_payment",
        "property",
    ]
    list_title = "Mortgages"
    formatters_columns = {
        "amount": display_dollars,
        "closing": display_dollars,
        "down_payment": display_percent,
        "monthly_payment": display_dollars,
        "property": link_to_property,
        "rate": display_percent,
        "start_date": display_date,
    }
    audit_fieldset = (
        "Audit",
        {
            "fields": ["created_by", "created_on", "changed_by", "changed_on"],
            "expanded": False,
        },
    )
    info_fieldset = (
        "Info",
        {
            "fields": [
                "property",
                "amount",
                "rate",
                "term",
                "down_payment",
                "monthly_payment",
                "start_date",
            ]
        },
    )
    show_fieldsets = [info_fieldset, audit_fieldset]

    @action(
        "amortization_schedule",
        "Amortization Schedule",
        icon="fa-calendar",
        multiple=False,
    )
    def amortization_schedule(self, mortgage: Mortgage) -> str:
        interest = mortgage.rate / 100
        principal = mortgage.amount * (1 - mortgage.down_payment / 100)
        term = mortgage.term
        loan = Loan(principal, interest, term)
        schedule = loan.schedule()
        if mortgage.start_date:
            dates = [
                mortgage.start_date + relativedelta(months=+i)
                for i in range(len(schedule))
            ]
        else:
            dates = None
        return self.render_template(
            "amortization_schedule.html",
            mortgage=mortgage,
            schedule=schedule,
            dates=dates,
        )


class PropertyView(ModelView, CompactCRUDMixin):
    """Configures the edit, list, and show views on the Property class."""

    datamodel = SQLAInterface(Property)
    add_exclude_columns = edit_exclude_columns = [
        "changed_by",
        "changed_on",
        "created_by",
        "created_on",
    ]
    description_columns = {
        "association_fee": "Annual home owner's association (HOA) fee.",
        "insurance": "Annual cost for home owner's insurance.",
        "land_value": "The value of the land which is not included in the depreciation of the property.",
        "management_fee": "Percentage of rental income cost for property management.",
        "nightly_rate": "Average Nightly Rate.",
        "occupancy": "Percentage of occupied nights.",
        "tax": "Annual property tax.",
    }
    label_columns = {
        "tax_deduction": "Tax Deduction",
        "total_expenses": "Total Expenses",
        "total_income": "Total Income",
        "total_inventory": "Inventory Value",
        "url": "URL",
    }
    list_columns = [
        "address",
        "cost",
        "total_monthly_cost",
        "total_monthly_revenue",
    ]
    list_title = "Properties"
    formatters_columns = {
        "association_fee": display_dollars,
        "cost": display_dollars,
        "changed_on": display_date,
        "created_on": display_date,
        "description": Markup,
        "insurance": display_dollars,
        "land_value": display_dollars,
        "management_fee": display_percent,
        "mortgage": link_to_mortgage,
        "nightly_rate": display_dollars,
        "occupancy": display_percent,
        "url": lambda x: Markup(f'<a href="{x}">{x}</a>'),
        "tax": display_dollars,
        "tax_deduction": display_table,
        "total_expenses": display_dollars,
        "total_income": display_dollars,
        "total_inventory": display_dollars,
        "total_monthly_cost": lambda x: Markup(
            f'<span style="color: red">{display_dollars(x)}</span>'
        ),
        "total_monthly_revenue": display_dollars,
    }
    audit_fieldset = (
        "Audit",
        {
            "fields": ["created_by", "created_on", "changed_by", "changed_on"],
            "expanded": False,
        },
    )
    expenses_fieldset = (
        "Expenses",
        {
            "fields": [
                "cost",
                "land_value",
                "association_fee",
                "insurance",
                "management_fee",
                "tax",
                "total_monthly_cost",
                "total_expenses",
                "tax_deduction",
            ]
        },
    )
    editable_expenses_fieldset = (
        "Expenses",
        {
            "fields": [
                "cost",
                "land_value",
                "association_fee",
                "insurance",
                "management_fee",
                "tax",
            ]
        },
    )
    income_fieldset = (
        "Income",
        {
            "fields": [
                "nightly_rate",
                "occupancy",
                "total_monthly_revenue",
                "total_income",
            ]
        },
    )
    editable_income_fieldset = (
        "Income",
        {
            "fields": [
                "nightly_rate",
                "occupancy",
            ]
        },
    )
    editable_info_fieldset = (
        "Info",
        {"fields": ["description", "url"], "expanded": False},
    )
    info_fieldset = (
        "Info",
        {"fields": ["total_inventory", "description", "url"], "expanded": False},
    )
    location_fieldset = (
        "Location",
        {"fields": ["address", "city", "state", "zipcode"]},
    )
    add_fieldsets = edit_fieldsets = [
        location_fieldset,
        editable_expenses_fieldset,
        editable_income_fieldset,
        editable_info_fieldset,
    ]
    show_fieldsets = [
        location_fieldset,
        expenses_fieldset,
        income_fieldset,
        info_fieldset,
        audit_fieldset,
    ]

    @action("financial_report", "Financial Report", icon="fa-report", multiple=False)
    def financial_report(self, property: Property) -> str:
        """Provide a summary of the finances of a property."""
        return self.render_template("financial_report.html", property=property)


ContactView.related_views = [PropertyView]
PropertyView.related_views = [
    BookingView,
    ContactView,
    ExpenseView,
    IncomeView,
    InventoryView,
    MortgageView,
]
appbuilder.add_view(
    PropertyView,
    "List Properties",
    category="Properties",
    icon="fa-table",
    category_icon="fa-home",
)
appbuilder.add_link(
    "Add Property", "PropertyView.add", icon="fa-plus", category="Properties"
)
appbuilder.add_view(
    MortgageView,
    "List Mortgages",
    icon="fa-table",
    category="Properties",
)
appbuilder.add_link(
    "Add Mortgage", "MortgageView.add", icon="fa-plus", category="Properties"
)
appbuilder.add_view(
    BookingView,
    "List Bookings",
    icon="fa-table",
    category="Bookings",
    category_icon="fa-suitcase",
)
appbuilder.add_link(
    "Add Booking", "BookingView.add", category="Bookings", icon="fa-plus"
)
appbuilder.add_view(
    ContactView,
    "List Contacts",
    icon="fa-table",
    category="Contacts",
    category_icon="fa-user",
)
appbuilder.add_link(
    "Add Contact", "ContactView.add", category="Contacts", icon="fa-plus"
)
appbuilder.add_view(
    ExpenseView,
    "List Expenses",
    icon="fa-table",
    category="Finance",
    category_icon="fa-money",
)
appbuilder.add_link(
    "Add Expense", "ExpenseView.add", icon="fa-plus", category="Finance"
)
appbuilder.add_view(IncomeView, "List Income", icon="fa-table", category="Finance")
appbuilder.add_link("Add Income", "IncomeView.add", icon="fa-plus", category="Finance")
appbuilder.add_view(
    InventoryView,
    "List Inventory",
    icon="fa-table",
    category="Inventory",
    category_icon="fa-truck",
)
appbuilder.add_link(
    "Add Item to Inventory",
    "InventoryView.add",
    icon="fa-plus",
    category="Inventory",
)
appbuilder.add_view(
    ContactEmailFormView, "Email Contact", icon="fa-envelope", category="Contacts"
)

"""
    Application wide 404 error handler
"""


@appbuilder.app.errorhandler(404)
def page_not_found(e):
    return (
        render_template(
            "404.html", base_template=appbuilder.base_template, appbuilder=appbuilder
        ),
        404,
    )


db.create_all()
