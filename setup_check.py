"""Verifie que l'environnement est lisible. Ne fait aucun traitement metier."""
import sqlite3, glob, sys

def ok(m): print(f"  [ok] {m}")
def ko(m): print(f"  [KO] {m}")

print("SQLite")
try:
    con = sqlite3.connect("data/risk.db")
    for t in ["ref_customer","ref_site","ref_contract","trd_deal",
              "mkt_forward_curve","mkt_spot_hourly","pos_snapshot"]:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        ok(f"{t:20s} {n:>9,} lignes")
except Exception as e:
    ko(f"risk.db illisible : {e}")

print("\nFichier plat back office")
try:
    with open("data/raw/bo_confirmations_20260724.csv", encoding="latin-1") as f:
        h = f.readline().strip()
    ok(f"en-tete : {h}")
    print("       -> separateur, decimale, encodage et format de date : a toi de voir")
except Exception as e:
    ko(e)

print("\nParquet")
parts = glob.glob("data/volumes_hourly/month=*/*.parquet")
ok(f"volumes_hourly : {len(parts)} partitions")
ok("actuals_daily.parquet present" if glob.glob("data/actuals_daily.parquet") else "actuals_daily.parquet ABSENT")

print("\npandas / numpy / pyarrow")
for m in ["numpy","pandas","pyarrow"]:
    try:
        __import__(m); ok(m)
    except ImportError: ko(f"{m} manquant")

print("\nPySpark")
try:
    import pyspark
    ok(f"pyspark {pyspark.__version__}")
    print("       -> verifie aussi que java -version repond (JDK 17 conseille)")
except ImportError:
    ko("pyspark manquant : pip install pyspark")
