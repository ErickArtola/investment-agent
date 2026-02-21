"""SQLite caching layer via SQLAlchemy."""
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Float, Text, DateTime, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from config.settings import DB_PATH

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
Base = declarative_base()
Session = sessionmaker(bind=engine)


class MetricsCache(Base):
    __tablename__ = "metrics"
    symbol = Column(String, primary_key=True)
    data = Column(Text)           # JSON
    updated_at = Column(DateTime)


class NewsCache(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, index=True)
    data = Column(Text)           # JSON list
    updated_at = Column(DateTime)


class ScoreCache(Base):
    __tablename__ = "scores"
    symbol = Column(String, primary_key=True)
    quantitative = Column(Float)
    qualitative = Column(Float)
    overall = Column(Float)
    recommendation = Column(String)
    justification = Column(Text)
    updated_at = Column(DateTime)


class Watchlist(Base):
    __tablename__ = "watchlist"
    symbol = Column(String, primary_key=True)
    added_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)


# ── Metrics ──────────────────────────────────────────────────────────────────

def save_metrics(symbol: str, data: dict):
    with Session() as s:
        obj = s.get(MetricsCache, symbol)
        if obj:
            obj.data = json.dumps(data)
            obj.updated_at = datetime.utcnow()
        else:
            s.add(MetricsCache(symbol=symbol, data=json.dumps(data), updated_at=datetime.utcnow()))
        s.commit()


def load_metrics(symbol: str, max_age_hours: int = 12) -> dict | None:
    with Session() as s:
        obj = s.get(MetricsCache, symbol)
        if obj and obj.updated_at > datetime.utcnow() - timedelta(hours=max_age_hours):
            return json.loads(obj.data)
    return None


# ── News ──────────────────────────────────────────────────────────────────────

def save_news(symbol: str, articles: list):
    with Session() as s:
        existing = s.query(NewsCache).filter_by(symbol=symbol).first()
        if existing:
            existing.data = json.dumps(articles)
            existing.updated_at = datetime.utcnow()
        else:
            s.add(NewsCache(symbol=symbol, data=json.dumps(articles), updated_at=datetime.utcnow()))
        s.commit()


def load_news(symbol: str, max_age_hours: int = 12) -> list | None:
    with Session() as s:
        obj = s.query(NewsCache).filter_by(symbol=symbol).first()
        if obj and obj.updated_at > datetime.utcnow() - timedelta(hours=max_age_hours):
            return json.loads(obj.data)
    return None


# ── Scores ────────────────────────────────────────────────────────────────────

def save_score(symbol: str, quant: float, qual: float, overall: float, rec: str, justification: str):
    with Session() as s:
        obj = s.get(ScoreCache, symbol)
        if obj:
            obj.quantitative = quant
            obj.qualitative = qual
            obj.overall = overall
            obj.recommendation = rec
            obj.justification = justification
            obj.updated_at = datetime.utcnow()
        else:
            s.add(ScoreCache(
                symbol=symbol, quantitative=quant, qualitative=qual,
                overall=overall, recommendation=rec,
                justification=justification, updated_at=datetime.utcnow(),
            ))
        s.commit()


def load_score(symbol: str, max_age_hours: int = 12) -> dict | None:
    with Session() as s:
        obj = s.get(ScoreCache, symbol)
        if obj and obj.updated_at > datetime.utcnow() - timedelta(hours=max_age_hours):
            return {
                "quantitative": obj.quantitative,
                "qualitative": obj.qualitative,
                "overall": obj.overall,
                "recommendation": obj.recommendation,
                "justification": obj.justification,
                "updated_at": obj.updated_at.strftime("%Y-%m-%d %H:%M"),
            }
    return None


def load_all_scores() -> list[dict]:
    with Session() as s:
        rows = s.query(ScoreCache).all()
        return [
            {
                "symbol": r.symbol,
                "quantitative": r.quantitative,
                "qualitative": r.qualitative,
                "overall": r.overall,
                "recommendation": r.recommendation,
                "justification": r.justification,
                "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M") if r.updated_at else "",
            }
            for r in rows
        ]


# ── Watchlist ─────────────────────────────────────────────────────────────────

def get_watchlist() -> list[str]:
    with Session() as s:
        return [r.symbol for r in s.query(Watchlist).all()]


def add_to_watchlist(symbol: str):
    with Session() as s:
        if not s.get(Watchlist, symbol):
            s.add(Watchlist(symbol=symbol))
            s.commit()


def remove_from_watchlist(symbol: str):
    with Session() as s:
        obj = s.get(Watchlist, symbol)
        if obj:
            s.delete(obj)
            s.commit()
