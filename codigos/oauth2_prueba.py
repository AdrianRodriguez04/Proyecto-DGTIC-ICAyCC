import os
from requests_oauthlib import OAuth2Session

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Solo para desarrollo local

# Configuración OAuth2
client_id = "" # ID de cliente
client_secret = "" # Secreto de cliente
redirect_uri = "http://localhost:8080" # URI de redirección
scope = ["openid",
        "https://www.googleapis.com/auth/userinfo.email",  
        "https://www.googleapis.com/auth/userinfo.profile"] # Scope de Google para obtener email y perfil 

# URLs oficiales de OAuth2 para Google
authorization_base_url = "https://accounts.google.com/o/oauth2/auth" # URL de autorización
token_url = "https://oauth2.googleapis.com/token" # URL para obtener el token

# Crear sesión OAuth2
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)

# 1. Obtener URL de autorización
authorization_url, state = oauth.authorization_url(
    authorization_base_url,
    access_type="offline", prompt="consent"  # Para obtener refresh token
)

print("Ir a esta URL y autorizar el acceso:")
print(authorization_url) 

# 2. Pegar la URL de callback
redirect_response = input("Pegar URL completa que redirigió Google: ")

# 3. Obtener el token de acceso
token = oauth.fetch_token(
    token_url,
    authorization_response=redirect_response,
    client_secret=client_secret
)

print("Token obtenido:", token)

# 4. Usar el token para hacer peticiones autenticadas
response = oauth.get("https://www.googleapis.com/oauth2/v1/userinfo")
print("Datos del usuario:,\n", response.json())
