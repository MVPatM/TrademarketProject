from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("mysql+pymysql://root:1234@localhost:3306/test", echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
