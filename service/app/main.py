from fastapi import FastAPI, Request, Response, Depends, Form, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
import os

from auth import verify_password, get_password_hash, create_access_token, get_current_user
from database import engine, Base, get_db
from database import User, Ads


# Создание таблиц БД
Base.metadata.create_all(bind=engine)


app = FastAPI()


# Берём абсолютный путь до папки, где лежит main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Jinja2 смотрит в папку templates внутри app/
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


# Начальная страница
@app.get("/")
def main_page(request: Request):
    return templates.TemplateResponse(request=request, name="main_page.html")


# Форма регистрации
@app.get("/register/", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


# Регистрация
@app.post("/register/")
def register(response: Response, 
             nickname: str = Form(...), 
             email: str = Form(...), 
             phone: str = Form(...), 
             password: str = Form(...), 
             db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(User).filter(or_(User.email == email, User.phone == phone)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email or phone already registered")
    
    # Hash the password and create the user
    hashed_password = get_password_hash(password)
    new_user = User(nickname=nickname, email=email, phone=phone, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate JWT token
    access_token = create_access_token(data={"sub": new_user.email})

    response = RedirectResponse(url=f"/profile/", status_code=302)
    response.set_cookie(key=f"Authorization", value=f"Bearer {access_token}", httponly=True)

    return response


# Форма авторизации
@app.get("/login/", response_class=HTMLResponse)
def login_form(request: Request):
    if request.cookies.get(f"Authorization"):
        response = RedirectResponse(url=f"/profile/", status_code=302)
    else:
        return templates.TemplateResponse("login.html", {"request": request})
    return response


# Авторизация
@app.post("/login/")
def login(response: Response,
          email: str = Form(...), 
          password: str = Form(...), 
          db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})

    response = RedirectResponse(url=f"/profile/", status_code=302)
    response.set_cookie(key=f"Authorization", value=f"Bearer {access_token}", httponly=True)

    return response


# Выход
@app.post("/logout/")
def logout(response: Response):
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key=f"Authorization")
    return response


# Форма профиля
@app.get("/profile/", response_class=HTMLResponse)
def profile(request: Request, db: Session = Depends(get_db)):
    if not request.cookies.get("Authorization"):
        return RedirectResponse(url="/", status_code=302)

    user = get_current_user(request, db)
    if isinstance(user, RedirectResponse):
        return user

    ads = db.query(Ads).filter(Ads.seller == user.email).order_by(Ads.header).all()

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "ads": ads,
    })


# Форма объявлений
@app.get("/ads/", response_class=HTMLResponse)
def get_ads(request: Request, response: Response, db: Session = Depends(get_db)):
    if not request.cookies.get(f"Authorization"):
        return RedirectResponse(url=f"/", status_code=302)

    user = get_current_user(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    ads = db.query(Ads).filter(Ads.is_private == False).order_by(Ads.header).all()
    
    return templates.TemplateResponse("ads.html", {
        "request": request,
        "user": user,
        "ads": ads,
    })


# Форма подачи объявления
@app.get("/upload/", response_class=HTMLResponse)
def upload_form(request: Request, db: Session = Depends(get_db)):
    if not request.cookies.get(f"Authorization"):
        return RedirectResponse(url=f"/", status_code=302)

    user = get_current_user(request, db)
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse("upload.html", {"request": request, "user": user})


# Подать объявление
@app.post("/upload/")
def upload(request: Request,
           response: Response, 
           header: str = Form(...), 
           description: str = Form(...), 
           price: str = Form(...), 
           db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    if not request.cookies.get("Authorization"):
        return RedirectResponse(url="/", status_code=302)
    print(user)
    new_ad = Ads(seller=user.email, header=header, description=description, price=price)
    db.add(new_ad)
    db.commit()
    db.refresh(new_ad)

    response = RedirectResponse(url=f"/profile/", status_code=302)

    return response


# Просмотр конкретного объявления
@app.get("/ads/{ad_id}/", response_class=HTMLResponse)
def view_ad(request: Request, ad_id: int, db: Session = Depends(get_db)):
    auth = request.cookies.get("Authorization")
    if not auth:
        return RedirectResponse(url="/", status_code=302)
    
    ad = db.query(Ads).filter(Ads.id == ad_id).first()
    
    if not ad:
        return HTMLResponse("Ad not found", status_code=404)
    
    user = get_current_user(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    if ad.is_private:
        print(f"DBG: {ad} {user}")
        if user.email != ad.seller:
            return HTMLResponse("You are not the owner!", status_code=405)

    seller = db.query(User).filter(User.email == ad.seller).first()
    seller_name = seller.nickname
    seller_phone = seller.phone
    
    return templates.TemplateResponse("ad.html", {
        "request": request,
        "seller": seller,
        "seller_name": seller_name,
        "seller_phone": seller_phone,
        "ad": ad,
        "user": user,
        "ad_id": ad.id,
    })

@app.get("/ads/{ad_id}/contact_info", response_class=PlainTextResponse)
def get_contact_info(request: Request, ad_id: int, db: Session = Depends(get_db)):
    auth = request.cookies.get("Authorization")
    if not auth:
        return RedirectResponse(url="/", status_code=302)
    
    ad = db.query(Ads).filter(Ads.id == ad_id).first()

    if not ad:
        return HTMLResponse("Ad not found", status_code=404)
    
    return PlainTextResponse(ad.seller)


# Изменить приватность
@app.post("/ads/edit_privacy/{ad_id}")
def edit_privacy(request: Request, ad_id: int, db: Session = Depends(get_db)):
    if not request.cookies.get("Authorization"):
        return RedirectResponse(url="/", status_code=302)
    
    user = get_current_user(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    ad = db.query(Ads).filter(Ads.id == ad_id).first()
    
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    
    if user.email == ad.seller:
        ad.is_private = not ad.is_private
        db.commit()
        return RedirectResponse(url="/profile/", status_code=302)
    else:
        raise HTTPException(
            status_code=403, 
            detail="You are not da owner!!"
        )
