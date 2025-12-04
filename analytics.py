import pandas as pd
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
    query = """
        SELECT
            substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2) AS date,
            SUM(revenue) AS total_revenue
        FROM sales
        WHERE vendor_id = ?
        GROUP BY date
        ORDER BY date;
    """
    df = pd.read_sql_query(query, engine, params=(vendor_id,))
    return df


def get_product_revenue_for_date(vendor_id: int, date_str: str):
    """
    Връща DataFrame с оборот по продукти за даден vendor и дата (YYYY-MM-DD):
    product_name, quantity, revenue
    """
    engine = db.get_sqlalchemy_engine()
    query = """
        SELECT
            product_name,
            SUM(quantity) AS quantity,
            SUM(revenue) AS revenue
        FROM sales
        WHERE vendor_id = ?
          AND substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2) = ?
        GROUP BY product_name
        ORDER BY revenue DESC;
    """
    df = pd.read_sql_query(query, engine, params=(vendor_id, date_str))
    return df
