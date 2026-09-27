from fastapi import APIRouter,Depends,HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import User,UserOut,create_access_token,get_current_user,verify_password
class TokenOut(BaseModel):
    access_token:str;token_type:str="bearer";user:UserOut
router=APIRouter(prefix="/api/v1/auth",tags=["Authentication"])
@router.post("/login",response_model=TokenOut)
def login(form:OAuth2PasswordRequestForm=Depends(),db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==form.username.lower()))
    if not user or not verify_password(form.password,user.password_hash): raise HTTPException(status_code=401,detail="Invalid email or password")
    return {"access_token":create_access_token(user),"token_type":"bearer","user":user}
@router.get("/me",response_model=UserOut)
def me(user:User=Depends(get_current_user)): return user
