import os
from typing import Dict, Any, List

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Text,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# === КОНФИГУРАЦИЯ НА БАЗАТА ===

# Ако има DATABASE_URL → ползваме него (Postgres в облака)
# Иначе падаме към локален SQLite (data.db)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data.db")

# Допълнителни аргументи за SQLite (check_same_thread)
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


# === ORM МОДЕЛИ ===

class ProductPrice(Base):
    __tablename__ = "product_prices"
    vendor_id = Column(Integer, nullable=False)
    product_id = Column(String, nullable=False)
    product_name = Column(Text, nullable=True)
    unit_price = Column(Float, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("vendor_id", "product_id", name="pk_product_prices"),
    )


class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(Integer, nullable=False)
    product_id = Column(String, nullable=False)
    product_name = Column(Text, nullable=False)
    timestamp = Column(String, nullable=False)  # 'dd.mm.yyyy/HH:MM'
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    revenue = Column(Float, nullable=False)


class LastStock(Base):
    __tablename__ = "last_stock"
    vendor_id = Column(Integer, nullable=False)
    product_id = Column(String, nullable=False)
    product_name = Column(Text, nullable=True)
    qty = Column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("vendor_id", "product_id", name="pk_last_stock"),
    )


# === ИНИЦИАЛИЗАЦИЯ НА БАЗАТА ===

def init_db():
    """Създава таблиците при първо пускане (ако ги няма)."""
    Base.metadata.create_all(bind=engine)


# === УТИЛИТИ ЗА СЕСИИ ===

def get_session() -> Session:
    return SessionLocal()


# === ФУНКЦИИ ЗА ЦЕНИ ===

def get_price(vendor_id: int, product_id: str):
    """Връща цената на даден продукт за даден vendor, ако има такава, иначе None."""
    session = get_session()
    try:
        pp: ProductPrice | None = (
            session.query(ProductPrice)
            .filter(
                ProductPrice.vendor_id == vendor_id,
                ProductPrice.product_id == product_id,
            )
            .one_or_none()
        )
        if pp:
            return float(pp.unit_price)
        return None
    finally:
        session.close()


def upsert_price(vendor_id: int, product_id: str, product_name: str, unit_price: float):
    """
    Задава / обновява цена за продукт. Може да се ползва от помощни скриптове.
    """
    session = get_session()
    try:
        pp: ProductPrice | None = (
            session.query(ProductPrice)
            .filter(
                ProductPrice.vendor_id == vendor_id,
                ProductPrice.product_id == product_id,
            )
            .one_or_none()
        )
        if pp is None:
            pp = ProductPrice(
                vendor_id=vendor_id,
                product_id=product_id,
                product_name=product_name,
                unit_price=unit_price,
            )
            session.add(pp)
        else:
            pp.product_name = product_name
            pp.unit_price = unit_price

        session.commit()
    finally:
        session.close()


# === ФУНКЦИЯ ЗА ВМЪКВАНЕ НА ПРОДАЖБА ===

def insert_sale(vendor_id: int, product_id: str, product_name: str,
                timestamp: str, quantity: int):
    """
    Вмъква продажба:
    - взима цената от product_prices;
    - ако няма цена – приема 0.0 (ще знаем, че липсва и трябва да я добавим).
    """
    price = get_price(vendor_id, product_id)
    if price is None:
        price = 0.0

    revenue = quantity * price

    session = get_session()
    try:
        sale = Sale(
            vendor_id=vendor_id,
            product_id=product_id,
            product_name=product_name,
            timestamp=timestamp,
            quantity=quantity,
            unit_price=price,
            revenue=revenue,
        )
        session.add(sale)
        session.commit()
    finally:
        session.close()


# === ФУНКЦИИ ЗА LAST_STOCK (състояние на наличностите) ===

def get_last_inventory_for_vendor(vendor_id: int) -> Dict[str, Dict[str, Any]]:
    """
    Връща dict {product_id: {"name": product_name, "qty": qty}}
    за даден vendor, на база last_stock.
    """
    session = get_session()
    try:
        rows: List[LastStock] = (
            session.query(LastStock)
            .filter(LastStock.vendor_id == vendor_id)
            .all()
        )

        inventory: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            inventory[str(r.product_id)] = {
                "name": r.product_name,
                "qty": int(r.qty),
            }
        return inventory
    finally:
        session.close()


def replace_inventory_for_vendor(vendor_id: int, inventory: Dict[str, Dict[str, Any]]):
    """
    Изтрива старото състояние за vendor_id и вкарва новото
    (цял snapshot на наличностите).
    inventory е dict {product_id: {"name": ..., "qty": ...}}
    """
    session = get_session()
    try:
        # Трием старите записи за този vendor
        session.query(LastStock).filter(LastStock.vendor_id == vendor_id).delete()

        # Вмъкваме новите
        objs = []
        for product_id, data in inventory.items():
            objs.append(
                LastStock(
                    vendor_id=vendor_id,
                    product_id=str(product_id),
                    product_name=data.get("name", ""),
                    qty=int(data.get("qty", 0)),
                )
            )

        if objs:
            session.add_all(objs)

        session.commit()
    finally:
        session.close()


# === ПОДПОМАГАНЕ НА PANDAS (analytics/report) ===

def get_sqlalchemy_engine():
    """
    Връща SQLAlchemy engine, който може да се ползва директно от pandas.read_sql_query.
    """
    return engine
