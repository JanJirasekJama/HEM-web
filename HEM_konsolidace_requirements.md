# HEM - business requirements pro slouceni 3 programu

## Vychodiska

Dokument konsoliduje businessove pozadavky z techto programu:

- `HEM-inventory.py` - evidence wellness/minibar/lobby odpisu, archiv a mesicni reporty.
- `HEM-comunicate.py` - recepcni vzkazy, ukoly, penezni denik, uzivatele, e-mail a zalohy.
- `HEM_Lite_zalohy (3).py` - zalohove faktury, archiv faktur, sluzby, splatnosti, reporty, zalohy a obnova.
- `Komunikace pokojské/` - webova komunikace recepce a pokojskych, ukolovani uklidu, fotodokumentace, minibar checklist, revize a pradelna.

Cilem slouceni je jedna aplikace HEM s jednotnym prihlasenim, spolecnym nastavenim, jednotnym ulozistem dat, centralnim archivem, jednotnymi reporty a sdilenymi ciselniky.

Cilova nova aplikace bude progresivni PWA webova aplikace v Reactu se shadcn/ui. Backend bude modulární monolit ve FastAPI nad PostgreSQL databazi a perzistentnim souborovym ulozistem. Aplikace bude nasazena na linuxovem serveru v Dockeru a vsechny hlavni sluzby musi byt soucasti hlavniho `docker-compose.yml`.

Aplikace musi byt navrzena modularne. Jednotlive business moduly nesmi byt primo zavisle jeden na druhem. Smí sdilet pouze spolecne jadro a sdilene sluzby, u kterych to dava smysl: uzivatele, role, opravneni, nastaveni, ciselniky, audit, notifikace, soubory, exporty, zalohy a spolecny design system.

## Hlavni business oblasti

### 1. Uzivatele, role a opravneni

- System musi podporovat prihlaseni uzivatelu jmenem a heslem.
- Hesla musi byt ukladana hashovana, ne jako cisty text.
- System musi podporovat minimalne role `admin`, `recepcni`, `ucetni` a `pokojska`.
- Admin musi mit pristup ke sprave uzivatelu, nastaveni, zaloham a vsem modulům.
- Role recepcni musi mit pristup k provoznim modulům: vzkazy, ukoly, penezni denik, faktury, archiv, sluzby dle opravneni.
- Role ucetni musi mit pristup hlavne k fakturam, archivum, platbam, danovym reportum a exportum.
- Role pokojska musi mit pristup k pridelenym uklidum, revizim, pradelne, fotkam, minibar checklistu a vlastnim poznamkam.
- U uzivatele musi byt evidovano datum vytvoreni, posledni prihlaseni, role, opravneni a pripadne barva komentaru.
- System nesmi dovolit smazani chraneneho admin uctu.
- System nesmi dovolit uzivateli smazat aktualne prihlaseny vlastni ucet.
- Pri slouceni je potreba sjednotit duplicitni spravu uzivatelu z komunikace a fakturace.

### 2. Spolecne nastaveni aplikace

- System musi evidovat nastaveni firmy/provozovny: nazev, adresa, ICO, DIC, provozovna, mena, sazba DPH.
- System musi podporovat tema aplikace (`system`, `light`, `dark`).
- System musi umoznit nastavit vystupni slozku pro soubory a archiv.
- System musi umoznit nastavit automaticke zalohy, interval zaloh, retenci zaloh a cilovou slozku.
- System musi umoznit nastavit SMTP server, port, uzivatelske jmeno, heslo, odesilatele, sablony predmetu a tela e-mailu.
- System musi podporovat volbu, zda po vytvoreni automaticky otevrit PDF.
- System musi podporovat konfiguraci poctu pokoju hotelu.
- System musi podporovat jazyk reportu a menu reportu, minimalne `CZK` jako vychozi menu.

### 2a. Modularita aplikace

- System musi byt rozdelen na nezavisle business moduly.
- Minimalni moduly jsou: core, inventory, komunikace/vzkazy, ukoly/kalendar, penezni denik, fakturace, reporting, housekeeping, notifikace, soubory, zalohy a migrace.
- Business modul nesmi primo importovat databazove modely, UI komponenty ani interni sluzby jineho business modulu.
- Komunikace mezi moduly musi probihat pres verejne kontrakty: API endpointy, aplikační sluzby, domenove udalosti nebo sdilene DTO/schema objekty.
- Sdilene jadro musi obsahovat pouze prurezove veci: auth, uzivatele, role/opravneni, nastaveni, audit log, ciselniky, cas, soubory, notifikace, exporty a transakcni infrastrukturu.
- Sdilene UI musi obsahovat pouze genericke komponenty a layout prvky, napr. tabulky, formulare, dialogy, filtry, prikazy, navigaci, prazdne stavy, toast/notifikace a shadcn/ui wrappery.
- Modul muze byt vypnuty nebo skryty podle opravneni bez rozbiti ostatnich modulu.
- Modul musi vlastnit svoje business entity, API routy, validace, migrace, testy a UI obrazovky.
- Sdilene ciselniky se maji pouzit jen tam, kde skutecne reprezentuji stejnou business entitu; jinak maji zustat oddelene. Priklad: inventory minibar polozky a housekeeping minibar checklist mohou mit vazbu, ale nejsou stejny modul.
- Reportovy modul muze cist agregovana data z ostatnich modulu pres read-only dotazy nebo reporting views, nesmi menit jejich stav.
- Notifikacni modul muze odebírat domenove udalosti ostatnich modulu, ale ostatni moduly nemaji znat jeho interní implementaci.
- Migracni modul muze zapisovat do vice modulu, ale pouze jako jednorazovy importni adapter s auditovatelnym vysledkem.

### 3. Ciselniky sluzeb, polozek a splatnosti

- System musi podporovat spravu sluzeb pro fakturaci v kategoriich, napr. Wellness, Ubytovani, Ostatni sluzby.
- Kazda sluzba musi mit nazev, cenu, typ, kategorii, stav aktivni/neaktivni a volitelny popis.
- Neaktivni sluzby se nemaji nabizet pro nove faktury, ale historicka data musi zustat citelna.
- System musi podporovat vlastni sluzbu pri vytvareni faktury, pokud je zadana rucni cena.
- System musi podporovat spravu splatnosti faktur.
- Splatnost musi mit nazev, hodnotu, jednotku (`hodiny` nebo `dny`) a stav aktivni/neaktivni.
- System musi podporovat spravu polozek pro wellness odpisy.
- System musi podporovat spravu polozek pro minibarove odpisy vcetne cen.
- System musi podporovat spravu polozek pro lobby vcetne informace, zda polozka ma cenu, a vychozi ceny.
- System musi podporovat spravu seznamu pokoju; pokoj muze byt cislo i pojmenovany pokoj/apartma, napr. `Deluxe`, `VIP` nebo `Afrika - 217`.
- System musi podporovat spravu typu povinnych fotek pro uklid, napr. postel, koupelna, podlaha, minibar, kos nebo virivka.
- System musi rozlisit fakturacni/inventory minibarove polozky od housekeeping minibar checklistu, protoze housekeeping checklist je evidence spotreby po pokoji bez ceny.
- Ciselnikove polozky musi mit nazev, jednotku, kategorii, aktivni stav a podle typu cenu.
- Pri mazani nebo deaktivaci ciselniku nesmi dojit ke ztrate historickych zaznamu.

### 4. Inventory / provozni odpisy

- System musi umoznit denni evidenci wellness odpisu podle datumu.
- Wellness odpis musi obsahovat mnozstvi jednotlivych aktivnich polozek a volitelnou poznamku.
- System musi umoznit denni evidenci minibarovych odpisu podle datumu.
- Minibar odpis musi obsahovat mnozstvi jednotlivych aktivnich polozek a volitelnou poznamku.
- System musi umoznit denni evidenci lobby prodeju/pozadavku podle datumu.
- Lobby zaznam musi podporovat standardni polozky s mnozstvim a pripadne cenou.
- Lobby zaznam musi podporovat vlastni polozky na prani s popisem, mnozstvim a cenou.
- Kazdy inventory zaznam musi mit datum, typ, data polozek, cas ulozeni a uzivatele.
- Ulozeni denniho zaznamu musi pridat zaznam do archivu.
- System musi umoznit nacist a upravit drive ulozena data pro vybrane datum.
- System musi umoznit mazat archivni zaznamy.
- System musi umoznit filtrovat archiv podle data, typu nebo textu.
- System musi generovat mesicni report wellness, minibar a lobby.
- Mesicni report musi scitat mnozstvi podle polozek a u lobby i financni hodnotu.
- Mesicni report musi jit exportovat do PDF a Excelu.

### 5. Recepcni vzkazy a smenova komunikace

- System musi umoznit kazdemu uzivateli psat vzkaz pro aktualni den.
- Pro kombinaci datum + uzivatel ma existovat prave jeden aktualni denni vzkaz; ulozeni prepisuje starsi verzi pro stejny den a uzivatele.
- Vzkazy musi podporovat prosty text i HTML formatovani.
- System musi podporovat historii vzkazu podle data a uzivatele.
- System musi umoznit vyhledavani v historii vzkazu.
- System musi umoznit otevrit detail historickeho vzkazu.
- System musi umoznit kopirovat historicky vzkaz do dnesniho vzkazu.
- System musi umoznit mazani historickych vzkazu.
- System musi podporovat komentare ke vzkazum vcetne barev podle uzivatele.
- System musi umoznit komentare pridat, upravit a smazat.
- System musi umoznit export vzkazu do textoveho souboru.
- System musi umoznit odeslat denni vzkazy e-mailem aktivnim prijemcum.
- E-mail vzkazu musi obsahovat doplnkove provozni pocty: snidane, prijezdy, odjezdy, prubehy a wellness.
- Predmet a telo e-mailu musi byt sablonovatelne.

### 6. Ukoly a kalendar

- System musi podporovat evidenci ukolu v kalendari.
- Ukol musi mit nazev, popis, termin, prioritu, prirazeni na konkretniho uzivatele nebo na vsechny a stav splneni.
- System musi podporovat jednorazove ukoly.
- System musi podporovat opakovane ukoly.
- Opakovani musi podporovat minimalne tydenni opakovani podle dnu v tydnu.
- Opakovani musi podporovat intervalove opakovani po N dnech.
- Opakovani musi podporovat volitelne datum konce.
- System musi zobrazit ukoly pro vybrany den v kalendari.
- System musi zobrazovat statistiku ukolu pro vybrany den: celkem, splnene, nesplnene, priority.
- System musi umoznit oznacit ukol jako splneny/nesplneny.
- U jednorazoveho ukolu musi byt stav splneni ulozen primo u ukolu.
- U opakovaneho ukolu musi byt stav splneni ulozen po jednotlivych vyskytovych datech.
- System musi umoznit trvale smazat ukol; u opakovanych ukolu se smaze cela serie vcetne splneni.
- Poznamka: ve zdrojovem programu je pouzivana trida `TaskEditDialog`, ale neni definovana; pri slouceni je nutne dodelat plnohodnotny formular pro vytvareni/upravu ukolu.

### 7. Penezni denik a smeny

- System musi umoznit evidovat hotovost na zacatku a konci smeny.
- Zaznam penezniho deniku musi mit datum, uzivatele, typ smeny, ranní hotovost, vecerni hotovost, rozdil, poznamku a cas zaznamu/upravy.
- System musi vypocitat rozdil jako `cash_end - cash_start`.
- System musi podporovat upravu a mazani zaznamu penezniho deniku.
- System musi zobrazovat historii penezniho deniku.
- System musi exportovat penezni denik do CSV.
- System musi automaticky urcit typ smeny podle smenoveho logu pro dany den a uzivatele.
- System musi evidovat smenovy log s uzivatelem, typem smeny, zacatkem, koncem, hotovosti a poznamkou.
- System musi sledovat stav penezniho deniku pro aktualni den.
- System musi upozornit na chybejici ranni hotovost.
- System musi po 20:00 upozornit na chybejici vecerni hotovost.
- Dashboard musi zobrazovat stav dnesni hotovosti a vcerejsi konecnou hotovost.

### 8. Zalohove faktury

- System musi umoznit vytvorit zalohovou fakturu pro zakaznika.
- Faktura musi obsahovat zakaznika, e-mail, telefon, sluzbu, termin, cenu, splatnost a poznamku.
- Termin musi byt validovan ve formatu `DD.MM.RRRR` nebo `DD.MM.RRRR HH:MM`.
- Pro vlastni sluzbu musi byt vyzadovana rucni cena.
- U prednastavene sluzby musi jit pouzit cena z ciselniku a volitelne procentualni navyseni.
- System musi vypocitat konkretni datum splatnosti podle zvolene splatnosti.
- System musi generovat unikatni cislo faktury.
- Cislo faktury musi slouzit jako variabilni symbol.
- System musi generovat PDF zalohove faktury.
- PDF musi obsahovat dodavatele, provozovnu, odberatele, kontakt, sluzbu, termin, cenu, platebni udaje, splatnost a storno podminky.
- Po vytvoreni faktury musi byt PDF ulozeno do archivu faktur.
- Vytvorena faktura musi byt pridana do datoveho archivu faktur.
- System musi umoznit automaticky otevrit PDF po vytvoreni.
- System musi umoznit odeslat fakturu e-mailem zakaznikovi a kopii odesilateli.
- E-mail faktury musi mit konfigurovatelnou SMTP konfiguraci a sablonu.

### 9. Archiv faktur a platby

- Archiv faktur musi evidovat cislo faktury, zakaznika, termin, datum vytvoreni, stav platby, splatnost, konkretni due date, cenu, sluzbu, poznamku, cestu k PDF, e-mail, telefon a uzivatele, ktery fakturu vydal.
- System musi automaticky urcovat stav platby podle splatnosti a casu vytvoreni.
- System musi podporovat minimalne stavy: neuhrazeno, uhrazeno, ceka na uhradu / pred splatnosti.
- System musi umoznit rucne oznacit fakturu jako uhrazenou.
- System musi umoznit rucne oznacit fakturu jako neuhrazenou.
- System musi umoznit smazat fakturu z archivu vcetne archivniho PDF.
- System musi umoznit otevrit PDF z archivu.
- System musi umoznit export archivu faktur do CSV.
- System musi prubezne aktualizovat stavy faktur podle splatnosti.

### 10. Reporty, statistiky a danove vystupy

- System musi poskytovat statistiky faktur za zvolene obdobi.
- Statistiky musi obsahovat pocet faktur, uhrazene/neuhrazene faktury, faktury k uhrade, celkovou castku, prumernou fakturu, nejcastejsi sluzbu a nejvyssi obrat podle sluzby.
- Statistiky musi podporovat graficke zobrazeni podle sluzeb a mesicu.
- Statistiky musi jit exportovat do CSV, PDF a Excelu.
- System musi generovat danovy report z archivu faktur.
- Danovy report musi pocitat celkove trzby, DPH podle nastavene sazby a ciste trzby.
- Danovy report musi obsahovat rozpad podle sluzeb.
- Danovy report musi jit exportovat a tisknout.
- System musi umoznit export pro danove priznani a export DPH.
- Spolecny reportovy modul by mel zahrnout provozni odpisy, vzkazy/penezni denik a fakturaci.

### 11. Zalohy, obnova a integrita

- System musi podporovat manualni zalohu dat.
- System musi podporovat automaticke zalohy podle nastaveni.
- System musi archivovat zalohy jako ZIP.
- System musi zahrnout do zaloh vsechny hlavni datove soubory/moduly.
- System musi podporovat retenci zaloh podle poctu dni nebo poctu verzi.
- System musi umoznit zobrazit existujici zalohy.
- System musi umoznit smazat zalohu.
- System musi podporovat body obnovy.
- Bod obnovy musi obsahovat cas, popis a snapshot dulezitych dat.
- System musi umoznit obnovit data z bodu obnovy.
- System by mel kontrolovat integritu aplikace/dat, protoze komunikacni modul obsahuje hash integrity.
- Pri slouceni je potreba sjednotit tri oddelene zalohovaci mechanismy do jednoho.

### 12. E-mail a prijemci

- System musi podporovat centralni SMTP konfiguraci.
- System musi podporovat prijemce pro denni recepcni vzkazy.
- Prijemce musi mit jmeno, e-mail a aktivni stav.
- System musi odesilat jen aktivnim prijemcum.
- System musi podporovat samostatnou sablonu pro vzkazy a samostatnou sablonu pro faktury.
- System musi validovat, ze pro odeslani existuje server, port, uzivatelske jmeno, heslo a odesilatel.

### 13. Housekeeping / komunikace pokojskych

- System musi podporovat modul pro komunikaci recepce a pokojskych.
- Modul musi fungovat jako live sdileny provozni board pro vice zarizeni pripojenych k serveru pres interni sit nebo HTTPS.
- Admin musi spravovat ucty, seznam pokoju, housekeeping minibar polozky a typy povinnych fotek.
- Recepce musi umet zadat uklid pro jeden nebo vice pokoju najednou.
- Zadani uklidu musi obsahovat pokoj, typ prace, prioritu, poznamku, povinne fotky a volitelne vlastni foto-ukoly.
- Typ prace musi podporovat minimalne `Prijezd`, `Odjezd`, `Prubeh` a `Jine ukoly`.
- Priorita musi podporovat minimalne `Normalni`, `Vysoka` a `Nizka`.
- Aktivni uklid musi mit stavy `Ceka`, `Uklizi se`, `Pozastaveno`, `Hotovo`, `Zkontrolovano`.
- Recepce musi videt stav pokoje, poznamku pokojské, vlozene fotky, cas zacatku, cas konce a dobu uklidu.
- Recepce musi umet upravit zadani, vratit pokoj k uklidu, smazat ukol a oznacit hotovy uklid jako zkontrolovany.
- Zkontrolovane ukoly musi jit skryt/archivovat z denniho seznamu.
- Pokojska musi videt aktivni pokoje k uklidu.
- Pokojska musi umet zahajit uklid; pri zahajeni se ulozi cas zacatku, pokojská a stav `Uklizi se`.
- Pokojska musi mit detail aktualniho uklidu jako mobilni workflow pro jeden pokoj.
- Pokojska musi umet uklid pozastavit a nasledne pokracovat; cas pozastaveni se nesmi zapocitat do ciste doby uklidu.
- Pokojska musi umet pridat poznamku k pokoji, napr. zavada, chybejici rucniky nebo host na pokoji.
- Pokojska musi umet dopsat dodatkovy ukol/praci v ramci pokoje; recepce musi videt, zda je dodatkovy ukol hotovy.
- Recepce musi vybrat, ktere fotky jsou pro dany uklid povinne.
- Pokud recepce nevybere zadnou povinnou fotku, uklid pujde ukoncit bez fotek.
- Pokojska nesmi ukoncit uklid, dokud nejsou vlozeny vsechny povinne fotky.
- Pokojska musi umet nahrat dobrovolnou fotku s vlastnim popisem, napr. zavada, flek nebo rozbite vybaveni.
- Fotky musi byt ukladane jako samostatne soubory, ne jako base64 v hlavni databazi.
- Fotka musi mit metadata: typ/ukol fotky, URL/cestu, cas vytvoreni, vazbu na uklid/revizi/pradelnu a priznak dobrovolnosti.
- System musi podporovat limit velikosti fotky, validaci typu souboru a idealne tvorbu nahledu.
- Pokojska musi umet vyplnit minibar checklist pro konkretni pokoj a uklid.
- Kazda minibar polozka muze byt u jednoho uklidoveho zadani zapsana jen jednou; vychozi mnozstvi je 1.
- System musi poskytovat mesicni prehled housekeeping minibaru podle pokoje, data a polozek.
- System musi umet exportovat housekeeping minibar report do PDF.
- Po ukonceni uklidu musi vzniknout zaznam historie vcetne pokoje, casu, pokojské, fotek, poznamek, dodatkovych ukolu a minibar zaznamu.
- Historie uklidu musi jit filtrovat po mesici a seskupovat podle data a pokojské.
- Recepce a admin musi umet zobrazit detail historie vcetne velkych fotek.
- Recepce a admin musi umet oznacit historicky zaznam jako `Zkontrolovano`.
- Admin musi umet upravit vybrane historicke udaje a smazat zaznam z historie.
- Pokojska musi umet zapsat dodatkovou praci mimo konkretni pokoj; tato prace se uklada do historie.
- System musi podporovat revizni ukoly mezi pokojskymi.
- Revizni ukol musi obsahovat misto, text zadani, stav, cas vytvoreni, cas dokonceni, resitele, poznamku a fotky.
- Revizni ukol musi mit stavy minimalne `open` a `done`.
- Pokojska musi umet revizni ukol splnit s poznamkou a vice fotkami.
- System musi podporovat workflow pradelna echo.
- Recepce musi umet vyvolat aktivni echo pradelny.
- Pokojska musi umet echo pradelny prevzit.
- Dokonceni pradelny musi vyzadovat fotku skrine s pradlem.
- Pradelna musi mit stavy `open`, `accepted`, `done`, `cancelled`.
- Hotova pradelna se musi ulozit do historie a zapocitat do mesicniho reportu prace pokojskych.
- System musi poskytovat mesicni report historie prace pokojskych: pocet pracovnich dni, pocet uklizenych pokoju a pocet prevzeti pradelny podle pokojské.
- Housekeeping modul musi podporovat real-time aktualizace pro recepci a mobilni zarizeni pokojskych.

### 14. Dashboard a provozni prehled

- Po prihlaseni musi system zobrazit dashboard.
- Dashboard musi ukazovat prihlaseneho uzivatele.
- Dashboard musi ukazovat pocet dnesnich vzkazu.
- Dashboard musi ukazovat pocet dnesnich nesplnenych ukolu.
- Dashboard musi zobrazovat seznam dnesnich nesplnenych ukolu.
- Dashboard musi zobrazovat stav penezniho deniku.
- Dashboard musi zobrazovat vcerejsi konecnou hotovost.
- Dashboard by mel upozornovat na provozni chyby, napr. chybejici hotovost nebo blizici se splatnosti faktur.
- Dashboard by mel zobrazovat aktivni housekeeping stav: pokoje cekajici na uklid, probihajici uklidy, hotove ke kontrole, aktivni pradelna a otevrene revize.

### 15. Import, export a kompatibilita

- System musi umet nacist stavajici JSON data ze vsech puvodnich zdroju.
- System musi umet nacist stavajici data z `Komunikace pokojské/data.json` a fotky ze slozky `Komunikace pokojské/photos/`.
- System musi zachovat historii z puvodnich archivu.
- System musi podporovat migraci starych vzkazu s polem `timestamp` na novy format `date/user/content`.
- System musi podporovat export dat do beznych formatu: CSV, TXT, PDF a Excel.
- System by mel podporovat import nebo obnovu dat ze zalohy.
- Pri migraci je potreba sjednotit formaty datumu, protoze puvodni programy pouzivaji `yyyy-MM-dd`, `dd.MM.yyyy`, `dd.MM.yyyy HH:mm` a ISO timestamp.
- Pri migraci pokojskych je potreba zachovat existujici vazby fotek ulozenych jako `/api/photos/<hash>.<ext>` a premapovat je do noveho souboroveho uloziste.

### 16. Technicke a provozni pozadavky

- Frontend nove aplikace bude React se shadcn/ui.
- Frontend musi byt implementovan jako progresivni webova aplikace (PWA).
- PWA musi byt instalovatelna na desktopu, tabletu a mobilu.
- PWA musi obsahovat web app manifest s nazvem aplikace, ikonami, theme color, display modem a start URL.
- PWA musi mit service worker pro cache statickych assetu a zakladni offline start aplikace.
- PWA musi podporovat offline fallback obrazovku pro situace, kdy backend neni dostupny.
- PWA musi pro mobilni workflow pokojskych podporovat pouziti fotoaparatu pres `input capture` nebo ekvivalentni browser API.
- PWA musi podporovat notifikace, pokud je uzivatel povoli.
- Notifikace musi byt konfigurovatelne podle role a modulu.
- Notifikace musi rozlisovat urgentni provozni udalosti a bezne informacni udalosti.
- System musi podporovat minimalne tyto notifikace: novy uklid pro pokojskou, zmena priority uklidu, nove echo pradelny, nova revize, hotovy pokoj ke kontrole, chybejici vecerni hotovost, blizici se splatnost faktury a novy komentar/vzkaz.
- Notifikace musi fungovat v otevrene aplikaci jako in-app toast/centrum notifikaci.
- Push notifikace mimo otevrenou aplikaci musi byt podporovany tam, kde to dovoluje prohlizec a nasazeni.
- Pokud push notifikace nejsou dostupne nebo nejsou povolene, musi existovat fallback na in-app notifikace a real-time udalosti.
- Uzivatel musi mit moznost notifikace povolit, zakazat a upravit podle typu udalosti.
- System musi evidovat dorucene/precetene notifikace, aby se neopakovaly bez duvodu.
- Backend nove aplikace bude FastAPI jako modulární monolit.
- Hlavni databaze bude PostgreSQL bezici jako sluzba v hlavnim Docker Compose stacku.
- Datova vrstva ma byt navrzena pres SQLAlchemy 2.0 a Alembic migrace.
- Backend musi poskytovat REST API pro bezne operace a SSE nebo WebSocket pro real-time aktualizace.
- Pro soucasny provoz recepce + pokojské staci Server-Sent Events; WebSocket je vhodny az pro plnohodnotny chat nebo obousmerne real-time editace.
- React build muze byt v produkci servirovan FastAPI backendem.
- Aplikace musi byt nasazena na linuxovem serveru v Dockeru.
- Hlavni `docker-compose.yml` musi obsahovat minimalne sluzby `backend`, `postgres` a podle zvoleneho servirovani `frontend` nebo reverzni proxy.
- Docker Compose musi definovat perzistentni volumes pro PostgreSQL data, uploady/fotky, PDF faktury, exporty, zalohy a recovery pointy.
- Docker Compose musi podporovat `.env` konfiguraci pro databazi, tajemstvi, SMTP, URL aplikace a notifikace.
- Docker Compose musi obsahovat healthcheck pro backend a PostgreSQL.
- Databazove migrace se musi spoustet kontrolovane pri deployi nebo startu backendu.
- Data jsou dnes ukladana do JSON souboru v `LOCALAPPDATA` a ve slozce `Komunikace pokojské`; po slouceni musi byt migrovana do jednotne databaze a souboroveho archivu.
- System musi mit perzistentni souborove uloziste v Docker volume nebo bind mountu pro PDF faktury, fotky, exporty, zalohy a recovery pointy.
- Aplikace musi branit paralelnimu prepisovani dat; vsechny zmeny musi prochazet backendem a databazovymi transakcemi.
- Aplikace musi byt spustitelna a restartovatelna pres Docker Compose a systemovou spravu serveru.
- PWA musi umet zobrazit offline fallback pri vypadku serveru nebo site; zapisove operace vyzaduji dostupny backend, pokud nebude pozdeji explicitne navrzen offline sync.
- Vsechny casove udaje musi byt ukladane konzistentne a zobrazovane v lokalnim formatu.
- System musi logovat, kdo vytvoril nebo upravil dulezity zaznam.
- Hesla musi pouzivat moderni hash, napr. Argon2id nebo bcrypt; legacy SHA/PBKDF2 hashe je treba migrovat pri prvnim prihlaseni nebo migraci.
- SMTP hesla a jina tajemstvi nesmi byt ukladana v cistem textu v databazi; provozni tajemstvi patri do `.env`, Docker secrets nebo jineho serveroveho secret managementu.
- Ciselne rady faktur musi vznikat atomicky v transakci.
- Fotky a velke prilohy musi mit limity velikosti, validaci MIME typu a zalohovaci strategii.
- Backend musi byt rozdelen po modulech, napr. `app/modules/inventory`, `app/modules/housekeeping`, `app/modules/invoicing`, `app/modules/communication`.
- Frontend musi byt rozdelen po feature modulech, napr. `src/features/inventory`, `src/features/housekeeping`, `src/features/invoicing`.
- Sdilene backend prvky patri do `app/core` nebo `app/shared`; sdilene frontend prvky patri do `src/shared` nebo `src/components`.
- Moduly musi mit jasne verejne rozhrani, aby slo pozdeji modul prepsat nebo vypnout bez zásahu do ostatnich modulu.

## Architektonicke rozhodnuti

### Zvoleny stack

- Frontend: React + TypeScript + shadcn/ui.
- Aplikacni vrstva: progresivni PWA s manifestem, service workerem, offline fallbackem, instalovatelnosti a notifikacemi.
- Backend: FastAPI jako modulární monolit.
- Databaze: PostgreSQL jako sluzba v Docker Compose, SQLAlchemy 2.0, Alembic migrace.
- Real-time: Server-Sent Events pro oznameni zmen stavu; frontend si po eventu dotahne aktualni data.
- Notifikace: centralni notifikacni modul, in-app notifikace pres real-time udalosti, push notifikace pres Web Push tam, kde je to v nasazeni dostupne.
- Soubory: perzistentni Docker volume nebo bind mount pro fotky, PDF faktury, exporty, zalohy a body obnovy.
- Background ulohy: APScheduler nebo ekvivalentni scheduler pro automaticke zalohy, aktualizaci splatnosti a pravidelne kontroly.
- Autentizace: serverove session v `HttpOnly` cookie nebo ekvivalentni cookie-based auth, CSRF ochrana pro mutacni requesty.
- Nasazeni: linuxovy server v Docker Compose; pristup z recepce a mobilu/tabletu pokojskych pres prohlizec.

### Modularni hranice

- Core modul: autentizace, uzivatele, role, opravneni, nastaveni, audit, systemovy cas, health check a globalni konfigurace.
- Shared services: soubory, notifikace, exporty, e-mail, zalohy, migrace a ciselniky pouzivane vice moduly.
- Business moduly: inventory, komunikace, ukoly, penezni denik, fakturace, housekeeping a reporting.
- Kazdy business modul ma vlastni API router, service vrstvu, DB modely/tabulky, Pydantic schemata, frontend routes, UI komponenty a testy.
- Business modul muze zaviset na core/shared vrstvach, ale nesmi zaviset primo na jinem business modulu.
- Pokud jeden modul potrebuje reagovat na zmenu v jinem modulu, pouzije domenovou udalost, napr. `housekeeping.assignment_done`, `invoice.overdue`, `cash.missing_evening_entry`.
- Pokud jeden modul potrebuje data jineho modulu pro cteni, pouzije verejnou query sluzbu nebo reporting view, ne primy pristup do interni logiky modulu.
- Databazove cizi klice mezi business moduly se maji pouzivat stridme; preferovane jsou stabilni identifikatory a snapshoty nazvu tam, kde je dulezita historie.

### Proc FastAPI + PostgreSQL v Dockeru

- Existujici business logika pro faktury, PDF, Excel, SMTP, migrace a zalohy je v Pythonu, takze FastAPI minimalizuje prepis.
- React/shadcn potrebuje ciste API, ne desktopovy PySide runtime.
- Housekeeping modul vyzaduje webovy provoz pro vice zarizeni a upload fotek z mobilu.
- PostgreSQL je vhodnejsi pro serverove nasazeni, soubezny provoz vice uzivatelu, transakce, reporting a budouci rust.
- Protoze PostgreSQL bude soucasti hlavniho Docker Compose stacku, nekomplikuje instalaci samostatnym externim databazovym serverem.
- Modulární monolit je vhodnejsi nez mikroservisy, protoze moduly sdili uzivatele, role, nastaveni, audit, soubory a reporty.
- PWA vrstva je vhodna, protoze pokojské potrebuji rychly mobilni pristup bez instalace z app storu a recepce potrebuje desktopovy provoz ve stejne aplikaci.

### Zamítnuté alternativy

- Node.js/NestJS + Prisma: dobre sedi k Reactu, ale znamenalo by to vetsí prepis existujici Python logiky pro PDF, Excel, SMTP a migrace.
- Django/DRF: robustni varianta, ale pro tento modulární lokalni system tezsi nez FastAPI.
- SQLite jako vychozi databaze: jednoduche pro lokalni instalaci, ale mene vhodne pro dockerizovany server s vice soubeznymi uzivateli a reportingem.
- Supabase/Firebase/cloud backend: nevhodne jako primarni reseni kvuli pozadavku na vlastni linuxovy server, lokalni Docker stack, fotky a PDF archiv.
- Electron/Tauri bez backendu: nevhodne, protoze pokojské potrebuji mobilni pristup, sdilene API, role, audit a souborove uploady.

## Hruby navrh datove struktury

Doporuceni: PostgreSQL databaze v Docker Compose plus perzistentni slozky/volumes pro prilohy:

```text
HEM/
  docker-compose.yml
  .env
  backend/
  frontend/
  data/
    postgres/
    files/
      invoices/
      photos/
      exports/
      backups/
      recovery/
```

### Docker Compose sluzby

```yaml
services:
  backend:
    image: hem-backend
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+psycopg://hem:${POSTGRES_PASSWORD}@postgres:5432/hem
      APP_BASE_URL: ${APP_BASE_URL}
      FILE_STORAGE_ROOT: /data/files
    volumes:
      - hem_files:/data/files

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: hem
      POSTGRES_USER: hem
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - hem_postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hem -d hem"]

  # Volitelne podle produkcniho baleni:
  # frontend/nginx/caddy/traefik pro servirovani PWA, HTTPS a reverse proxy.

volumes:
  hem_postgres:
  hem_files:
```

Poznamka: ukazka je orientacni, finalni compose musi resit porty, HTTPS/reverse proxy, backup joby, logovani a politiku restartu.

### Core tabulky

```sql
users (
  id TEXT PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  display_name TEXT,
  role_id TEXT NOT NULL,
  comment_color TEXT,
  cannot_delete INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  last_login_at TEXT,
  active INTEGER DEFAULT 1
);

roles (
  id TEXT PRIMARY KEY,
  name TEXT UNIQUE NOT NULL
);

permissions (
  id TEXT PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  description TEXT
);

role_permissions (
  role_id TEXT NOT NULL,
  permission_id TEXT NOT NULL,
  PRIMARY KEY (role_id, permission_id)
);

settings (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL
);

audit_log (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  user_id TEXT,
  created_at TEXT NOT NULL,
  before_json TEXT,
  after_json TEXT
);

media_files (
  id TEXT PRIMARY KEY,
  module TEXT NOT NULL, -- housekeeping|invoices|reports|other
  original_name TEXT,
  storage_path TEXT NOT NULL,
  public_url TEXT,
  mime_type TEXT,
  sha256 TEXT,
  size_bytes INTEGER,
  width INTEGER,
  height INTEGER,
  thumbnail_path TEXT,
  created_by TEXT,
  created_at TEXT NOT NULL
);

notification_preferences (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  channel TEXT NOT NULL, -- in_app|push|email
  enabled INTEGER DEFAULT 1,
  UNIQUE (user_id, event_type, channel)
);

notifications (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'info', -- info|warning|urgent
  title TEXT NOT NULL,
  body TEXT,
  entity_type TEXT,
  entity_id TEXT,
  action_url TEXT,
  created_at TEXT NOT NULL,
  delivered_at TEXT,
  read_at TEXT
);

push_subscriptions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  p256dh TEXT NOT NULL,
  auth TEXT NOT NULL,
  user_agent TEXT,
  created_at TEXT NOT NULL,
  last_used_at TEXT,
  active INTEGER DEFAULT 1,
  UNIQUE (endpoint)
);

module_registry (
  id TEXT PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  enabled INTEGER DEFAULT 1,
  sort_order INTEGER DEFAULT 0
);
```

### Ciselniky

```sql
service_categories (
  id TEXT PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  sort_order INTEGER DEFAULT 0,
  active INTEGER DEFAULT 1
);

services (
  id TEXT PRIMARY KEY,
  category_id TEXT,
  name TEXT NOT NULL,
  type TEXT,
  price REAL NOT NULL DEFAULT 0,
  description TEXT,
  active INTEGER DEFAULT 1
);

due_terms (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  value INTEGER NOT NULL DEFAULT 0,
  unit TEXT NOT NULL, -- hours|days
  active INTEGER DEFAULT 1
);

inventory_items (
  id TEXT PRIMARY KEY,
  module TEXT NOT NULL, -- wellness|minibar|lobby
  name TEXT NOT NULL,
  unit TEXT DEFAULT 'ks',
  category TEXT,
  price REAL,
  has_price INTEGER DEFAULT 0,
  active INTEGER DEFAULT 1,
  sort_order INTEGER DEFAULT 0
);

hotel_rooms (
  id TEXT PRIMARY KEY,
  label TEXT UNIQUE NOT NULL,
  floor TEXT,
  room_type TEXT,
  sort_order INTEGER DEFAULT 0,
  active INTEGER DEFAULT 1
);

housekeeping_minibar_items (
  id TEXT PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  sort_order INTEGER DEFAULT 0,
  active INTEGER DEFAULT 1
);

photo_task_types (
  id TEXT PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  sort_order INTEGER DEFAULT 0,
  active INTEGER DEFAULT 1
);

email_recipients (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  active INTEGER DEFAULT 1
);
```

### Housekeeping / pokojské

```sql
housekeeping_assignments (
  id TEXT PRIMARY KEY,
  room_id TEXT NOT NULL,
  room_label_snapshot TEXT NOT NULL,
  work_type TEXT NOT NULL, -- arrival|departure|stayover|other
  priority TEXT NOT NULL DEFAULT 'normal',
  reception_note TEXT,
  status TEXT NOT NULL, -- waiting|cleaning|paused|done|checked
  archived INTEGER DEFAULT 0,
  created_by TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  started_at TEXT,
  finished_at TEXT,
  duration_seconds INTEGER,
  paused_seconds INTEGER DEFAULT 0,
  pause_started_at TEXT,
  housekeeper_id TEXT,
  housekeeper_name_snapshot TEXT,
  housekeeper_note TEXT,
  checked_at TEXT,
  checked_by TEXT
);

housekeeping_assignment_required_photos (
  id TEXT PRIMARY KEY,
  assignment_id TEXT NOT NULL,
  photo_task_type_id TEXT,
  label_snapshot TEXT NOT NULL,
  required INTEGER DEFAULT 1
);

housekeeping_photos (
  id TEXT PRIMARY KEY,
  assignment_id TEXT,
  revision_task_id TEXT,
  laundry_task_id TEXT,
  media_file_id TEXT NOT NULL,
  task_label TEXT NOT NULL,
  voluntary INTEGER DEFAULT 0,
  created_by TEXT,
  created_at TEXT NOT NULL
);

housekeeping_extra_tasks (
  id TEXT PRIMARY KEY,
  assignment_id TEXT NOT NULL,
  text TEXT NOT NULL,
  source TEXT DEFAULT 'housekeeping',
  done INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  done_at TEXT
);

housekeeping_minibar_entries (
  id TEXT PRIMARY KEY,
  assignment_id TEXT NOT NULL,
  room_id TEXT,
  room_label_snapshot TEXT NOT NULL,
  item_id TEXT,
  item_name_snapshot TEXT NOT NULL,
  quantity REAL DEFAULT 1,
  note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT
);

housekeeping_history (
  id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL, -- cleaning|additional_work|laundry
  source_id TEXT,
  history_date TEXT NOT NULL,
  housekeeper_id TEXT,
  housekeeper_name_snapshot TEXT,
  room_id TEXT,
  room_label_snapshot TEXT,
  work_type TEXT,
  status TEXT,
  summary TEXT,
  payload_json TEXT,
  saved_at TEXT NOT NULL,
  checked_at TEXT,
  checked_by TEXT
);

housekeeping_revision_tasks (
  id TEXT PRIMARY KEY,
  location TEXT NOT NULL,
  text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  created_by TEXT,
  created_at TEXT NOT NULL,
  completed_at TEXT,
  completed_by TEXT,
  completed_by_name_snapshot TEXT,
  note TEXT
);

housekeeping_laundry_tasks (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL, -- open|accepted|done|cancelled
  created_by TEXT,
  created_at TEXT NOT NULL,
  accepted_at TEXT,
  accepted_by TEXT,
  accepted_by_name_snapshot TEXT,
  completed_at TEXT,
  cancelled_at TEXT
);

housekeeping_additional_work (
  id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  housekeeper_id TEXT,
  housekeeper_name_snapshot TEXT,
  created_at TEXT NOT NULL,
  finished_at TEXT NOT NULL
);
```

### Inventory / odpisy

```sql
inventory_entries (
  id TEXT PRIMARY KEY,
  entry_date TEXT NOT NULL,
  module TEXT NOT NULL, -- wellness|minibar|lobby
  note TEXT,
  created_by TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT
);

inventory_entry_items (
  id TEXT PRIMARY KEY,
  entry_id TEXT NOT NULL,
  item_id TEXT,
  custom_description TEXT,
  quantity REAL NOT NULL,
  unit_price REAL,
  total_price REAL,
  is_custom INTEGER DEFAULT 0
);
```

### Vzkazy, ukoly a smeny

```sql
messages (
  id TEXT PRIMARY KEY,
  message_date TEXT NOT NULL,
  user_id TEXT NOT NULL,
  content_text TEXT NOT NULL,
  content_html TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  UNIQUE (message_date, user_id)
);

message_comments (
  id TEXT PRIMARY KEY,
  message_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  content_text TEXT NOT NULL,
  color TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT
);

tasks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  due_date TEXT NOT NULL,
  assigned_to_user_id TEXT,
  assigned_to_all INTEGER DEFAULT 0,
  priority TEXT DEFAULT 'Normalni',
  recurrence_type TEXT, -- null|weekly|interval
  recurrence_days_json TEXT,
  recurrence_interval_days INTEGER,
  recurrence_end_date TEXT,
  completed INTEGER DEFAULT 0,
  completed_by TEXT,
  completed_at TEXT,
  created_by TEXT,
  created_at TEXT NOT NULL
);

task_occurrence_completions (
  task_id TEXT NOT NULL,
  occurrence_date TEXT NOT NULL,
  completed_by TEXT,
  completed_at TEXT NOT NULL,
  PRIMARY KEY (task_id, occurrence_date)
);

cash_diary_entries (
  id TEXT PRIMARY KEY,
  entry_date TEXT NOT NULL,
  user_id TEXT NOT NULL,
  shift_type TEXT,
  cash_start REAL DEFAULT 0,
  cash_end REAL DEFAULT 0,
  difference REAL DEFAULT 0,
  notes TEXT,
  recorded_at TEXT,
  edited_at TEXT,
  edited_by TEXT,
  UNIQUE (entry_date, user_id)
);

shift_log (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  shift_type TEXT,
  start_time TEXT NOT NULL,
  end_time TEXT,
  cash_start REAL DEFAULT 0,
  cash_end REAL DEFAULT 0,
  notes TEXT
);
```

### Faktury a platby

```sql
invoice_counters (
  year INTEGER PRIMARY KEY,
  last_number INTEGER NOT NULL
);

invoices (
  id TEXT PRIMARY KEY,
  invoice_number TEXT UNIQUE NOT NULL,
  customer_name TEXT NOT NULL,
  customer_email TEXT,
  customer_phone TEXT,
  service_id TEXT,
  service_name_snapshot TEXT NOT NULL,
  event_at TEXT NOT NULL,
  price REAL NOT NULL,
  currency TEXT DEFAULT 'CZK',
  due_term_id TEXT,
  due_term_name_snapshot TEXT,
  due_date TEXT NOT NULL,
  note TEXT,
  payment_status TEXT NOT NULL, -- pending|paid|unpaid|overdue|cancelled
  pdf_path TEXT,
  issued_by TEXT,
  issued_at TEXT NOT NULL,
  paid_at TEXT,
  updated_at TEXT
);

invoice_emails (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  recipient_email TEXT NOT NULL,
  sent_at TEXT,
  success INTEGER NOT NULL,
  error_message TEXT
);
```

### Reporty, zalohy a obnova

```sql
exports (
  id TEXT PRIMARY KEY,
  export_type TEXT NOT NULL,
  module TEXT NOT NULL,
  period_from TEXT,
  period_to TEXT,
  file_path TEXT NOT NULL,
  created_by TEXT,
  created_at TEXT NOT NULL
);

backups (
  id TEXT PRIMARY KEY,
  file_path TEXT NOT NULL,
  created_at TEXT NOT NULL,
  created_by TEXT,
  backup_type TEXT, -- manual|auto
  size_bytes INTEGER,
  note TEXT
);

recovery_points (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  created_by TEXT,
  description TEXT,
  data_snapshot_path TEXT NOT NULL
);
```

## Navrh JSON konfigurace v tabulce `settings`

```json
{
  "company": {
    "name": "Wellness Hotel Beethoven",
    "address": "Beethovenova 1146, 430 01 Chomutov",
    "company_id": "",
    "company_vat": "",
    "branch_name": "",
    "branch_address": "",
    "num_rooms": 30
  },
  "ui": {
    "theme": "system",
    "language": "cs"
  },
  "finance": {
    "currency": "CZK",
    "tax_rate": 21,
    "open_pdf_after_create": true
  },
  "email": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "",
    "password_secret_ref": "",
    "sender": "recepce@hotelbeethoven.cz",
    "message_subject_template": "Vzkazy z recepce - {date}",
    "message_body_template": "...",
    "invoice_body_template": "..."
  },
  "backup": {
    "enabled": true,
    "path": "/data/files/backups",
    "interval_days": 7,
    "keep_days": 10,
    "versions_to_keep": 10
  },
  "housekeeping": {
    "photo_max_mb": 6,
    "allowed_photo_types": ["image/jpeg", "image/png", "image/webp"],
    "require_laundry_photo": true,
    "default_work_types": ["Prijezd", "Odjezd", "Prubeh", "Jine ukoly"],
    "default_priorities": ["Normalni", "Vysoka", "Nizka"]
  },
  "realtime": {
    "enabled": true,
    "transport": "sse",
    "poll_fallback_seconds": 2
  },
  "pwa": {
    "enabled": true,
    "installable": true,
    "offline_fallback": true,
    "asset_cache_strategy": "stale-while-revalidate",
    "push_notifications": true
  },
  "modules": {
    "inventory": true,
    "communication": true,
    "tasks": true,
    "cash_diary": true,
    "invoicing": true,
    "housekeeping": true,
    "reporting": true
  },
  "deployment": {
    "runtime": "docker-compose",
    "database": "postgresql",
    "file_storage_root": "/data/files",
    "public_base_url": ""
  }
}
```

## Migracni mapovani ze stavajicich souboru

| Puvodni soubor | Cilova oblast |
| --- | --- |
| `HEM_InventoryManager/settings.json` | `settings` |
| `wellness_items.json`, `minibar_items.json`, `lobby_items.json` | `inventory_items` |
| `wellness_data.json`, `minibar_data.json`, `lobby_data.json` | `inventory_entries`, `inventory_entry_items` |
| `archive_data.json` z inventory | `inventory_entries` + audit/export historie |
| `HEM_Komunikace/users.json` | `users`, `roles`, `role_permissions` |
| `messages.json` | `messages`, pripadne `message_comments` |
| `tasks.json`, `task_completions.json` | `tasks`, `task_occurrence_completions` |
| `cash_diary.json`, `shift_log.json` | `cash_diary_entries`, `shift_log` |
| `email_recipients.json` | `email_recipients` |
| `HEM_ZalohoveFaktury/services.json` | `service_categories`, `services` |
| `splatnosti.json` | `due_terms` |
| `archiv_data.json` z fakturace | `invoices` |
| `archiv_faktur/*.pdf` | `files/invoices/` |
| `backups/`, recovery data | `backups`, `recovery_points` |
| `Komunikace pokojské/data.json` | `hotel_rooms`, `housekeeping_*`, `media_files`, `users` |
| `Komunikace pokojské/photos/*` | `files/photos/`, `media_files`, `housekeeping_photos` |

## Otevrene body pred implementaci

- Potvrdit finalni produkcni topologii Docker Compose: zda bude PWA servirovat backend, nginx, Caddy nebo Traefik, a jak bude reseno HTTPS.
- Sjednotit terminologii: `wellness odpis`, `minibar odpis`, `lobby`, `vzkaz`, `ukol`, `penezni denik`, `zalohova faktura`.
- Urcit finalni role a opravneni podle realneho provozu.
- Rozhodnout, jestli ma inventory a fakturace sdilet jeden ciselnik sluzeb/polozek, nebo zustanou oddelene.
- Rozhodnout, jak se housekeeping minibar checklist propise do provozniho inventory/minibar reportingu.
- Doresit bezpecne ulozeni SMTP hesla a pripadne zapamatovaneho prihlaseni.
- Dodelat chybejici formular pro vytvareni/upravu ukolu.
- Navrhnout migracni skript, ktery nacte puvodni adresare v `LOCALAPPDATA`, slozku `Komunikace pokojské`, fotky a naplni novou databazi.
