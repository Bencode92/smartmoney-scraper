"""
Pipeline optimisé pour construire l'univers consolidé SmartMoney.
Utilise RUN_ID pour la cohérence des données.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from loguru import logger

from src.config import RAW_HF_DIR, RAW_DTR_DIR, PROCESSED_DATA_DIR
from src.utils.parsing import normalize_ticker
from src.utils.io import load_df, save_df, get_latest_file

# Configuration
RUN_ID = os.getenv("RUN_ID", datetime.now().strftime("%Y%m%d"))
MIN_SCORE_THRESHOLD = int(os.getenv("MIN_SCORE_THRESHOLD", "5"))

logger.add(
    PROCESSED_DATA_DIR / f"pipeline_{RUN_ID}.log",
    level="INFO",
    format="{time} | {level} | {message}"
)


def load_data_for_run(run_id: str) -> Dict[str, pd.DataFrame]:
    """
    Load all data for a specific run ID.
    Falls back to latest files if run_id files don't exist.
    """
    data = {}
    
    # HedgeFollow data
    hf_funds_file = RAW_HF_DIR / f"funds_{run_id}.csv"
    if not hf_funds_file.exists():
        hf_funds_file = RAW_HF_DIR / "funds_latest.csv"
    if hf_funds_file.exists():
        data["hf_funds"] = load_df(hf_funds_file)
        logger.info(f"Loaded {len(data['hf_funds'])} HF funds")
    
    hf_holdings_file = RAW_HF_DIR / f"holdings_{run_id}.csv"
    if not hf_holdings_file.exists():
        hf_holdings_file = get_latest_file(RAW_HF_DIR, "holdings_*.csv")
    if hf_holdings_file and hf_holdings_file.exists():
        data["hf_holdings"] = load_df(hf_holdings_file)
        logger.info(f"Loaded {len(data['hf_holdings'])} HF holdings")
    
    hf_insiders_file = RAW_HF_DIR / f"insiders_{run_id}.csv"
    if not hf_insiders_file.exists():
        hf_insiders_file = get_latest_file(RAW_HF_DIR, "insiders_*.csv")
    if hf_insiders_file and hf_insiders_file.exists():
        data["hf_insiders"] = load_df(hf_insiders_file)
        logger.info(f"Loaded {len(data['hf_insiders'])} HF insider trades")
    
    # Dataroma data
    dtr_managers_file = RAW_DTR_DIR / f"managers_{run_id}.csv"
    if not dtr_managers_file.exists():
        dtr_managers_file = RAW_DTR_DIR / "managers_latest.csv"
    if dtr_managers_file.exists():
        data["dtr_managers"] = load_df(dtr_managers_file)
        logger.info(f"Loaded {len(data['dtr_managers'])} DTR managers")
    
    dtr_holdings_file = RAW_DTR_DIR / f"holdings_{run_id}.csv"
    if not dtr_holdings_file.exists():
        dtr_holdings_file = get_latest_file(RAW_DTR_DIR, "holdings_*.csv")
    if dtr_holdings_file and dtr_holdings_file.exists():
        data["dtr_holdings"] = load_df(dtr_holdings_file)
        logger.info(f"Loaded {len(data['dtr_holdings'])} DTR holdings")
    
    dtr_grand_file = RAW_DTR_DIR / f"grand_portfolio_{run_id}.csv"
    if not dtr_grand_file.exists():
        dtr_grand_file = get_latest_file(RAW_DTR_DIR, "grand_portfolio_*.csv")
    if dtr_grand_file and dtr_grand_file.exists():
        data["dtr_grand"] = load_df(dtr_grand_file)
        logger.info(f"Loaded {len(data['dtr_grand'])} Grand Portfolio entries")
    
    return data


def aggregate_holdings(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Aggregate holdings from both sources by ticker.
    """
    aggregations = []
    
    # HedgeFollow Holdings
    if "hf_holdings" in data and not data["hf_holdings"].empty:
        df = data["hf_holdings"].copy()
        df["ticker"] = df["ticker"].apply(normalize_ticker)
        
        hf_agg = df.groupby("ticker").agg({
            "fund_id": "nunique",
            "weight_in_fund": lambda x: x[x > 0].mean() if len(x[x > 0]) else 0,
            "value_usd": "sum",
            "company_name": "first"
        }).reset_index()
        
        hf_agg.rename(columns={
            "fund_id": "num_hf",
            "weight_in_fund": "avg_weight_hf",
            "value_usd": "total_value_hf"
        }, inplace=True)
        
        aggregations.append(hf_agg)
        logger.info(f"Aggregated {len(hf_agg)} tickers from HF holdings")
    
    # Dataroma Holdings
    if "dtr_holdings" in data and not data["dtr_holdings"].empty:
        df = data["dtr_holdings"].copy()
        df["ticker"] = df["ticker"].apply(normalize_ticker)
        
        dtr_agg = df.groupby("ticker").agg({
            "manager_id": "nunique",
            "weight_in_portfolio": lambda x: x[x > 0].mean() if len(x[x > 0]) else 0,
            "value_usd": "sum",
            "company_name": "first"
        }).reset_index()
        
        dtr_agg.rename(columns={
            "manager_id": "num_si",
            "weight_in_portfolio": "avg_weight_si",
            "value_usd": "total_value_si"
        }, inplace=True)
        
        aggregations.append(dtr_agg)
        logger.info(f"Aggregated {len(dtr_agg)} tickers from DTR holdings")
    
    # Grand Portfolio
    if "dtr_grand" in data and not data["dtr_grand"].empty:
        df = data["dtr_grand"].copy()
        df["ticker"] = df["ticker"].apply(normalize_ticker)
        df["in_grand_portfolio"] = True
        
        grand_agg = df[["ticker", "num_investors", "total_value_usd", "avg_weight", "in_grand_portfolio"]].copy()
        grand_agg.rename(columns={
            "num_investors": "grand_num_investors",
            "total_value_usd": "grand_total_value",
            "avg_weight": "grand_avg_weight"
        }, inplace=True)
        
        aggregations.append(grand_agg)
        logger.info(f"Added {len(grand_agg)} tickers from Grand Portfolio")
    
    # Merge all aggregations
    if not aggregations:
        logger.warning("No data to aggregate")
        return pd.DataFrame()
    
    result = aggregations[0]
    for agg_df in aggregations[1:]:
        result = pd.merge(
            result, agg_df, on="ticker", how="outer", suffixes=("", "_dup")
        )
        
        # Handle duplicate columns
        for col in result.columns:
            if col.endswith("_dup"):
                base_col = col[:-4]
                result[base_col] = result[base_col].fillna(result[col])
                result.drop(col, axis=1, inplace=True)
    
    # Fill missing values
    numeric_cols = result.select_dtypes(include=['float64', 'int64']).columns
    result[numeric_cols] = result[numeric_cols].fillna(0)
    result["in_grand_portfolio"] = result.get("in_grand_portfolio", False).fillna(False)
    
    return result


def calculate_smartmoney_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate SmartMoney score for each ticker.
    """
    # Initialize score
    df["smartmoney_score"] = 0
    
    # Score components (adjust weights as needed)
    if "num_hf" in df.columns:
        df["smartmoney_score"] += df["num_hf"] * 2  # 2 points per HF
    
    if "num_si" in df.columns:
        df["smartmoney_score"] += df["num_si"] * 3  # 3 points per SI
    
    if "in_grand_portfolio" in df.columns:
        df["smartmoney_score"] += df["in_grand_portfolio"].astype(int) * 5  # 5 bonus
    
    if "grand_num_investors" in df.columns:
        df["smartmoney_score"] += df["grand_num_investors"] * 0.5  # 0.5 per grand investor
    
    # Add concentration bonus (high average weight = high conviction)
    if "avg_weight_hf" in df.columns:
        df["smartmoney_score"] += (df["avg_weight_hf"] > 3).astype(int) * 2
    
    if "avg_weight_si" in df.columns:
        df["smartmoney_score"] += (df["avg_weight_si"] > 5).astype(int) * 3
    
    # Round score
    df["smartmoney_score"] = df["smartmoney_score"].round(1)
    
    return df


def build_universe() -> pd.DataFrame:
    """
    Build the complete SmartMoney universe.
    """
    logger.info(f"Building universe for RUN_ID: {RUN_ID}")
    
    # Load data
    data = load_data_for_run(RUN_ID)
    
    if not data:
        logger.error("No data available")
        return pd.DataFrame()
    
    # Aggregate
    universe = aggregate_holdings(data)
    
    if universe.empty:
        logger.error("Failed to aggregate data")
        return universe
    
    # Calculate scores
    universe = calculate_smartmoney_score(universe)
    
    # Filter by minimum score
    initial_count = len(universe)
    universe = universe[universe["smartmoney_score"] >= MIN_SCORE_THRESHOLD]
    logger.info(f"Filtered by score >= {MIN_SCORE_THRESHOLD}: {initial_count} -> {len(universe)}")
    
    # Sort by score
    universe = universe.sort_values("smartmoney_score", ascending=False)
    
    # Add metadata
    universe["run_id"] = RUN_ID
    universe["generated_at"] = datetime.now().isoformat()
    
    # Clean up
    universe = universe[universe["ticker"].str.len() > 0]
    universe = universe[~universe["ticker"].str.match(r'^\d+$', na=False)]
    
    logger.info(f"Universe built: {len(universe)} tickers")
    
    # Log top stocks
    if len(universe) > 0:
        logger.info("Top 5 stocks by score:")
        for idx, row in universe.head(5).iterrows():
            logger.info(f"  {row['ticker']}: {row.get('company_name', 'N/A')} (score: {row['smartmoney_score']})")
    
    return universe


def main():
    """Main entry point."""
    universe = build_universe()
    
    if not universe.empty:
        # Save with RUN_ID
        output_file = PROCESSED_DATA_DIR / f"universe_smartmoney_{RUN_ID}.csv"
        save_df(universe, output_file)
        
        # Also save as latest
        save_df(universe, PROCESSED_DATA_DIR / "universe_latest.csv")
        
        # Statistics
        print(f"\n{'='*60}")
        print(f"SmartMoney Universe Built")
        print(f"{'='*60}")
        print(f"Run ID: {RUN_ID}")
        print(f"Total tickers: {len(universe)}")
        print(f"Output: {output_file}")
        print(f"Score threshold: >= {MIN_SCORE_THRESHOLD}")
        print(f"Top score: {universe['smartmoney_score'].max():.1f}")
        print(f"{'='*60}")
        
        # Top 10
        print("\nTop 10 SmartMoney Stocks:")
        print("-" * 60)
        for idx, row in universe.head(10).iterrows():
            print(f"{idx+1:2}. {row['ticker']:6} | {row.get('company_name', 'N/A')[:30]:30} | Score: {row['smartmoney_score']:5.1f}")
        print(f"{'='*60}\n")
    else:
        logger.error("Empty universe - no data to save")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
