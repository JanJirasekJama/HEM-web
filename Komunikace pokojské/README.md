# HEM - Housekeeping

Lokální webová aplikace pro komunikaci mezi recepcí a pokojskými.

## Spuštění pro více uživatelů live

Pro spolupráci více lidí najednou nespouštěj `index.html` přímo. Musí běžet server:

```powershell
node server.js
```

Na počítači, kde server běží, otevři:

`http://127.0.0.1:4173`

Ostatní zařízení ve stejné Wi-Fi síti otevřou adresu, kterou server vypíše do terminálu, například:

`http://192.168.1.20:4173`

Změny se ukládají do `data.json` a ostatním otevřeným uživatelům se propíšou live.

## Spuštění přes Docker

```powershell
docker compose up -d --build
```

Aplikace poběží na:

`http://127.0.0.1:4173`

`docker-compose.yml` připojuje lokální `data.json` a `photos/` do kontejneru, takže data a fotky zůstanou zachované i po restartu nebo přestavění image.

## Spuštění přes VS Code Live Server

Live Server sám neumí sdíleně ukládat data. Nech proto současně běžet i synchronizační server:

```powershell
node server.js
```

Aplikaci pak můžeš otevřít přes Live Server, například na `http://127.0.0.1:5500`. Prohlížeč si automaticky najde synchronizaci na stejné adrese a portu `4173`. Pokud běží backend jinde, přidej do adresy parametr `?sync=http://IP-ADRESA:4173`.

## Spuštění jen pro zkoušku

Soubor `index.html` jde pořád otevřít přímo v prohlížeči, ale v tomto režimu nejsou data sdílená mezi uživateli.

## Přihlášení

Přihlášení ověřuje server. Hesla se v `data.json` ukládají jen jako PBKDF2 hash, klient nikdy nedostává hodnotu hesla ani hash. Session běží přes `HttpOnly` cookie a zápisy na API vyžadují CSRF token.

Výchozí admin účet zná pouze zřizovatel. Další účty se nastavují v administraci. Při úpravě účtu nechte pole hesla prázdné, pokud se heslo nemá změnit.

## Role

Admin:
- nastavuje účty,
- nastavuje seznam pokojů,
- nastavuje položky minibaru,
- nastavuje seznam položek, které může recepce vybrat k vyfocení.

Recepční:
- zadává pokoje k úklidu,
- nastavuje typ práce, prioritu a poznámku,
- vybírá, jestli musí pokojská něco vyfotit; když nevybere nic, fotky nejsou povinné,
- vidí přijaté fotky, stav pokoje a čas úklidu,
- hotový pokoj otevře dvojklikem do detailu s velkou fotkou,
- vidí historii předchozích úklidů včetně fotek a jména pokojské,
- může hotový pokoj označit jako zkontrolovaný.

Pokojská:
- vidí pokoje k úklidu,
- odklikne začátek úklidu, tím se začne počítat čas a otevře se detail konkrétního pokoje,
- může úklid pozastavit; recepce tento stav vidí,
- nahrává povinné kontrolní fotky,
- zapisuje minibar checklistem; každá položka je u jednoho pokoje jen jednou,
- nemůže ukončit úklid, dokud nejsou vložené všechny povinné fotky.

## Důležité

Tato verze už umí lokální spolupráci více uživatelů přes jeden spuštěný server. Je vhodná pro provoz v jedné lokální síti.

Server nepublikuje `data.json` jako statický soubor a API stav vrací pouze přihlášeným uživatelům. Fotky se ukládají samostatně v adresáři `photos/`; `data.json` drží jen metadata a URL. Díky tomu se při synchronizaci nepřenáší obří base64 JSON. `/api/state` navíc používá ETag, takže nezměněný stav vrací `304` bez těla.

Pro veřejný internet bude pořád potřeba nasadit HTTPS, zálohy a produkční databázi.
