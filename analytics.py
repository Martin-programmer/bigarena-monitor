import pandas as pd
from sqlalchemy import text

import db


def get_vendors_list():
    """
    Връща списък с vendor-и, взети от таблицата sales и product_prices,
    за да покажем само тези, за които има данни.
    """
    engine = db.get_sqlalchemy_engine()

    query = """
        SELECT DISTINCT vendor_id FROM (
            SELECT vendor_id FROM sales
            UNION
            SELECT vendor_id FROM product_prices
        ) t
        ORDER BY vendor_id;
    """
    df = pd.read_sql_query(query, engine)
    return df["vendor_id"].tolist()


def get_daily_revenue_df(vendor_id: int):
    """
    Връща DataFrame с дневен оборот за даден vendor:
    колони: date (YYYY-MM-DD), total_revenue
    """
    engine = db.get_sqlalchemy_engine()
    query = text(
        """
        SELECT
            substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2) AS date,
            SUM(revenue) AS total_revenue
        FROM sales
        WHERE vendor_id = :vendor_id
        GROUP BY date
        ORDER BY date;
        """
    )
    df = pd.read_sql_query(query, engine, params={"vendor_id": vendor_id})
    return df


def get_product_revenue_for_date(vendor_id: int, date_str: str):
    """
    Връща DataFrame с оборот по продукти за даден vendor и дата (YYYY-MM-DD):
    product_name, quantity, revenue
    """
    engine = db.get_sqlalchemy_engine()
    query = text(
        """
        SELECT
            product_name,
            SUM(quantity) AS quantity,
            SUM(revenue) AS revenue
        FROM sales
        WHERE vendor_id = :vendor_id
          AND (substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2)) = :date_str
        GROUP BY product_name
        ORDER BY revenue DESC;
        """
    )
    df = pd.read_sql_query(
        query,
        engine,
        params={"vendor_id": vendor_id, "date_str": date_str},
    )
    return df


# ====== НОВИ ФУНКЦИИ ЗА ПЕРИОД ======

def get_vendor_date_bounds(vendor_id: int):
    """
    Връща (min_date, max_date) за даден vendor на база sales.
    Формат: 'YYYY-MM-DD' като string-ове. Ако няма данни -> (None, None)
    """
    engine = db.get_sqlalchemy_engine()
    query = text(
        """
        SELECT
            MIN(substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2)) AS min_date,
            MAX(substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2)) AS max_date
        FROM sales
        WHERE vendor_id = :vendor_id;
        """
    )
    df = pd.read_sql_query(query, engine, params={"vendor_id": vendor_id})
    if df.empty or df["min_date"].iloc[0] is None:
        return None, None
    return df["min_date"].iloc[0], df["max_date"].iloc[0]


def get_vendor_stats_for_period(vendor_id: int, date_from: str, date_to: str):
    """
    Връща:
    - daily_df: дневен оборот за периода (колони date, total_revenue)
    - total_revenue: общ оборот
    - total_qty: общ брой продадени артикули
    - avg_per_day: среден оборот на ден
    """
    engine = db.get_sqlalchemy_engine()

    # Дневна агрегация
    query_daily = text(
        """
        SELECT
            substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2) AS date,
            SUM(revenue) AS total_revenue
        FROM sales
        WHERE vendor_id = :vendor_id
          AND (substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2))
              BETWEEN :date_from AND :date_to
        GROUP BY date
        ORDER BY date;
        """
    )
    daily_df = pd.read_sql_query(
        query_daily,
        engine,
        params={"vendor_id": vendor_id, "date_from": date_from, "date_to": date_to},
    )

    if daily_df.empty:
        return daily_df, 0.0, 0, 0.0

    total_revenue = float(daily_df["total_revenue"].sum())

    # Общо количество за периода
    query_qty = text(
        """
        SELECT SUM(quantity) AS total_qty
        FROM sales
        WHERE vendor_id = :vendor_id
          AND (substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2))
              BETWEEN :date_from AND :date_to;
        """
    )
    qty_df = pd.read_sql_query(
        query_qty,
        engine,
        params={"vendor_id": vendor_id, "date_from": date_from, "date_to": date_to},
    )
    total_qty = (
        int(qty_df["total_qty"].iloc[0])
        if not qty_df.empty and qty_df["total_qty"].iloc[0] is not None
        else 0
    )

    # Среден оборот на ден
    num_days = daily_df["date"].nunique()
    avg_per_day = total_revenue / num_days if num_days > 0 else 0.0

    return daily_df, total_revenue, total_qty, avg_per_day


def get_top_products_for_period(vendor_id: int, date_from: str, date_to: str, limit: int = 20):
    """
    Връща DataFrame с TOP продукти за даден vendor и период:
    product_name, total_qty, total_revenue
    """
    engine = db.get_sqlalchemy_engine()
    query = text(
        f"""
        SELECT
            product_name,
            SUM(quantity) AS total_qty,
            SUM(revenue) AS total_revenue
        FROM sales
        WHERE vendor_id = :vendor_id
          AND (substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2))
              BETWEEN :date_from AND :date_to
        GROUP BY product_name
        ORDER BY total_revenue DESC
        LIMIT {limit};
        """
    )
    df = pd.read_sql_query(
        query,
        engine,
        params={"vendor_id": vendor_id, "date_from": date_from, "date_to": date_to},
    )
    return df


def get_all_vendors_revenue_for_period(date_from: str, date_to: str):
    """
    Връща DataFrame с общ оборот по vendor за даден период:
    vendor_id, total_revenue
    """
    engine = db.get_sqlalchemy_engine()
    query = text(
        """
        SELECT
            vendor_id,
            SUM(revenue) AS total_revenue
        FROM sales
        WHERE (substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2))
              BETWEEN :date_from AND :date_to
        GROUP BY vendor_id
        ORDER BY total_revenue DESC;
        """
    )
    df = pd.read_sql_query(
        query,
        engine,
        params={"date_from": date_from, "date_to": date_to},
    )
    return df
