"""Reproducible synthetic inventory, isolated in a new account."""

from datetime import datetime, time, timedelta

import numpy as np

from extensions import db
from models import Supplier, User
from services.inventory import create_item, stock_change

PRODUCTS = [
    "Wireless Mouse",
    "USB Keyboard",
    "HDMI Cable",
    "USB-C Hub",
    "Laptop Stand",
    "Webcam",
    "Headset",
    "Monitor",
    "Ethernet Cable",
    "Power Adapter",
    "Notebook",
    "Ballpoint Pen",
    "Printer Paper",
    "Sticky Notes",
    "Desk Organizer",
    "Whiteboard Marker",
    "Stapler",
    "Document Folder",
    "Envelope",
    "Packing Tape",
    "Coffee Beans",
    "Tea Bags",
    "Paper Cups",
    "Hand Soap",
    "Cleaning Wipes",
    "AA Batteries",
    "LED Bulb",
    "Shipping Box",
    "Bubble Wrap",
    "Label Roll",
]


def generate_demo(username, password, end_date, days=180, seed=42):
    if User.query.filter_by(username=username).first():
        raise ValueError("Username already exists. Choose a NEW demo username; existing data is untouched.")
    if days < 30 or days > 730 or len(password) < 8:
        raise ValueError("Use 30–730 days and a password of at least 8 characters.")
    rng = np.random.default_rng(seed)
    start = end_date - timedelta(days=days - 1)
    user = User(username=username, created_at=datetime.combine(start, time.min))
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.flush()
        suppliers = [
            Supplier(user_id=user.id, name=name, created_at=user.created_at)
            for name in [
                "Teal Office Supply",
                "Northline Electronics",
                "Harbor Packaging",
                "Daily Essentials",
            ]
        ]
        db.session.add_all(suppliers)
        db.session.flush()
        for i, name in enumerate(PRODUCTS):
            base = 5 + i % 12
            item = create_item(
                user.id,
                dict(
                    name=name,
                    quantity=base * 35,
                    price=round(2.5 + i * 3.7, 2),
                    category="electronics" if i < 10 else "consumable",
                    supplier_id=suppliers[i % 4].id,
                    description="Seeded demonstration product",
                ),
                created_at=user.created_at,
            )
            for index in range(days):
                day = start + timedelta(days=index)
                # Weekly seasonality, gradual trend, bounded noise and controlled spikes.
                seasonal = 1.35 if day.weekday() < 5 else 0.45
                units = max(1, int(round(base * seasonal * (1 + index / days * 0.25) + rng.normal(0, 1.2))))
                injected = i % 6 == 0 and index in {days - 20, days - 7}
                if injected:
                    units *= 9
                if item.quantity < units + base * 7:
                    stock_change(
                        item,
                        user.id,
                        base * 30,
                        "receipt",
                        "Scheduled replenishment",
                        datetime.combine(day, time(8)),
                    )
                stock_change(
                    item,
                    user.id,
                    -units,
                    "consumption",
                    "Controlled demo anomaly" if injected else "Daily consumption",
                    datetime.combine(day, time(17)),
                )
        db.session.commit()
        return user
    except Exception:
        db.session.rollback()
        raise
