# AI HANDOFF
## Update po dalším přerušení

Codex už na tomto úkolu pokračoval podle tohoto AI_HANDOFF.md, ale během dalšího běhu znovu narazil na 5hodinový usage limit.

Uživatel neví přesně, co Codex během posledního běhu stihl dokončit. Aktuální workspace proto může obsahovat:
- dokončené změny,
- rozpracované změny,
- částečně upravené soubory,
- nekonzistentní stav mezi backendem, frontendem, testy a commity.

Při dalším resume nejdřív:
1. přečti celý tento soubor,
2. spusť `git status`,
3. spusť `git diff --stat`,
4. spusť `git diff`,
5. zkontroluj poslední commity pomocí `git log --oneline -10`,
6. zrekonstruuj, co bylo hotové už před tímto během a co přibylo v posledním běhu,
7. pokračuj pouze z aktuálního stavu workspace.

Nezačínej od nuly. Nezahazuj žádné změny bez výslovného potvrzení uživatele.

## Kontext
Codex ve VS Code běžel na úkolu, ale během vykonávání došel 5hodinový limit / usage limit. Progress bar ve VS Code se točí, ale agent zřejmě nepokračuje.

## Cíl původního úkolu
Jsi lead architect tohoto projektu, a máš následující zadání
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
- Složité feature flow nejdřív rozdělit: čisté funkce → hooky → komponenty.

## Aktuální stav
- Změny v pracovním stromu jsou aktuálně v repozitáři.
- Před pokračováním zkontroluj `git status` a `git diff`.
- Nezahazuj žádné existující změny bez výslovného souhlasu.

## Pokyny pro pokračování
1. Projdi aktuální změny v repozitáři.
2. Urči, co už je hotové a co je rozdělané.
3. Nepřepisuj hotové části naslepo.
4. Dokonči původní úkol inkrementálně.
5. Po každém větším kroku spusť relevantní testy / build.
6. Na konci shrň změny a uveď, co zbývá.

## Důležité
Pokračuj z aktuálního stavu workspace, ne od nuly.

## Doporučený prompt pro další resume

Pokračuj přesně z aktuálního stavu workspace. Nezačínej od nuly.

Tento projekt už byl několikrát přerušen kvůli 5hodinovému Codex usage limitu. Uživatel neví přesně, co bylo v posledním běhu dokončeno.

Nejdřív si přečti celý AI_HANDOFF.md.

Potom spusť:
- git status
- git diff --stat
- git diff
- git log --oneline -10

Zrekonstruuj:
- co už je hotové,
- co je rozpracované,
- co může být nekonzistentní,
- jaký je nejbezpečnější další krok.

Nezahazuj žádné změny bez mého potvrzení.
Nepřepisuj hotové části naslepo.
Pokračuj inkrementálně v původním úkolu.
Pracuj po menších krocích.
Po každém větším kroku spusť relevantní test/build/lint.

Na začátku mi nejdřív napiš stručné shrnutí zjištěného stavu a navrhni další krok.