# Předchozí použité commandy

Jsi nový lead architekt tohoto projektu. 
Tvůj úkol je rozdělaný projekt vzít, zkontrolovat, vymyslet a připravit AI_HANDOFF.md pro dodělání projektu. K dispozici máš původní zadání úkolu, původní soubory na kterých projekt vznikl: HEM-comunicate.py, HEM-inventory.py, HEM_Lite_zalohy.py, web aplikaci ve složce Komunikace pokojské a rozdělaný projekt. 
Také máš k dispozici předešlé zadané prompty:
"
Přečti soubor s requirements a současné Python / JS aplikace, a implementuj onen plán v requirements.

Nejdříve bootstrapni základ projektu (backend, frontend, aby fungoval "prázdný"), a poté
Implementuj sdílenou core logiku,
Poté pro každou oblast:,
-- Definuj plán pro subagenta
-- Napiš testy pro backend dané oblasti
-- Předej implementaci subagentovi. Ten nesmí testy měnit bez tvého povolení, dbej zásad TDD.

Poté předej jinému subagentovi kontrolu onoho plánu. Mělo by jít o zero-trust přístup, kde veškerý kód a předpoklady si navzájem kontrolují subagenti. Ty pouze orchestruješ a kontroluješ adherence s požadavky.

Pro shadcn/ui generuj komponenty správným způsobem skrz npx, nezkoušej je psát sám.

Pro notifikace / queuing využij Redis, implementuj jej i do plánu.

Využij Git, boostrapni si repo a změny průběžně commituj"

a pozdější 

"Jsi lead architect tohoto projektu, a máš následující zadání
- Zkontroluj, zda je backend plně implementován, drží se principů TDD, a je v souladu s requirementy
- Poté, co si budeš jist, že je backend hotový, posuň se na vytváření kompletního frontendu (viz požadavky)
Zadávej samotnou implementaci subagentům (GPT-5.5 medium), pouze orchestruj a kontroluj. Využívej i "auditujícího" subagenta, tak aby vývoj probíhal za pomocí zero-trust přístupu. Zároveň využij jednoho GPT-5.4 low agenta, co bude držet a kontrolovat to-do list - ten na začátku vygeneruj, a nepřestávej dokud nebude kompletně splněný.

Výsledky průběžně commituj na git.

Dbej na využívání komponentů v Reactu, neduplikuj kód. Zde máš pár základních guidelines:
- App.tsx držet jako composition root: jen skládá hooky a sekce, bez business logiky a velkých efektů.
- Doménovou orchestrace přesunout do custom hooků, např. useSomethingController.
- Komponenty mají konzumovat data a handlery z hooků, ne sahat přímo do globálního store.
- Výběr a UI stav držet centrálně a jasně modelovat, aby nemohly být aktivní konfliktní stavy najednou.
- Dlouhé async operace, fetchování, debounce a cancellation patří do hooků, ne přímo do view komponent.
- U async efektů explicitně řešit cleanup, typicky přes AbortController.
- View komponenty držet co nejvíc jako čisté render funkce nebo malé komponenty s lokálním UI stavem.
- Nepřidávat zbytečné useState / useEffect, pokud jde hodnotu odvodit z props nebo store.
- Sdílenou a opakovanou UI strukturu vytáhnout do primitives/factories místo kopírování podobných card/list/modal layoutů.
- Modaly držet řízené zvenku přes isOpen, onClose, confirm/cancel handlery.
- Modal state držet mimo samotný modal; uvnitř modalu jen formulářový stav.
- Akce v modalech a listech mají mít stabilní id, nepoužívat indexy jako keys.
- U mutable listů vždy používat stabilní doménové ID jako React key.
- Duplicitní derived logiku vytahovat do helperů nebo hooků.
- Importovat explicitně z konkrétních modulů, vyhýbat se re-exportování všeho přes index.ts.
- Business logiku a výpočty držet mimo komponenty, ideálně v lib/, hooks/ nebo store vrstvě.
- Pro uživatelské chování psát testy přes pozorovatelný DOM, stav nebo doménové výpočty.
- Testovat hlavně hooky, utility, render plány, formuláře a interakce komponent.
- Před commitem odstranit unused importy, zkontrolovat duplicity a spustit testy/lint.
- Komentáře psát hlavně na vysvětlení „proč“, ne „co“.
- Názvy proměnných a funkcí držet čitelné, bez zbytečných zkratek.
- Komponenty pojmenovávat PascalCase, hooky useThing, utility podle okolních souborů.
- Pro UI konzistenci používat sdílené primitives/design systém místo ad hoc stylování v každém leaf komponentu.
- Složité feature flow nejdřív rozdělit: čisté funkce → hooky → komponenty." 

Zkontroluj co již bylo z těchto úkolů splněno (používej subagenty) a nepřestávej dokud nebudeš mít AI_HANDOFF.md hotový