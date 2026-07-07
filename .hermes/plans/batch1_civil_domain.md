# Terra.OS — Domain Expertise: Roboty Ziemne (CPV 45112000-5)
## Civil Engineer Batch #1 — Axiom Corpus L1 + Taksonomia CPV + Wzorce Kosztorysowe

**Data:** 2026-07-07  
**Autor:** Civil Engineer Agent 🏗️ — Agency Agents  
**Wersja:** 1.0  
**Dotyczy:** Engine L1 (clingo + Z3), kategoria robót CPV klasa C — Roboty Ziemne

---

## CZĘŚĆ 1: AXIOM CORPUS — 50 Reguł Walidacyjnych (CPV 45112000-5)

### Format axiomatu
Każdy aksjomat zdefiniowany jest wg schematu: ID | Kategoria | Treść | Przykład naruszenia | Severity | clingo_hint

---

### KATEGORIA: MASS_BALANCE (Bilans Mas)

---

#### AX-001
| Pole | Wartość |
|------|---------|
| **ID** | AX-001 |
| **Kategoria** | mass_balance |
| **Treść** | Bilans mas musi być zachowany: objętość wykopów ≈ objętość nasypów + urobek wywieziony ± tolerancja 5% |
| **Przykład naruszenia** | Przedmiar: wykop 10 000 m³, nasyp 6 000 m³, wywóz 2 000 m³. Brakuje 2 000 m³ wyjaśnienia. |
| **Severity** | CRITICAL |
| **clingo_hint** | `mass_imbalance(T) :- wykop_vol(T,V1), nasyp_vol(T,V2), wywoz_vol(T,V3), |V1-(V2+V3)| > 0.05*V1.` |
| **Norma** | PN-B-06050:1999 §4.2, KNR 2-01 |

---

#### AX-002
| Pole | Wartość |
|------|---------|
| **ID** | AX-002 |
| **Kategoria** | mass_balance |
| **Treść** | Współczynnik spulchnienia gleby musi być uwzględniony przy wywozie urobku (kat. I–IV: 1.05–1.40) |
| **Przykład naruszenia** | Wykop 1 000 m³ gliny kat. III (spulchnienie 1.25), a wywóz wyceniony na 1 000 m³ zamiast 1 250 m³ |
| **Severity** | WARNING |
| **clingo_hint** | `spulchnienie_error(T,P) :- pozycja_wywoz(T,P,V), pozycja_wykop(T,P2,Vw), kategoria_gruntu(P2,K), wskaznik_spulchnienia(K,Ws), V < Vw*Ws*0.95.` |
| **Norma** | KNR 2-01 tab. 0102, PN-EN 1997-1 |

---

#### AX-003
| Pole | Wartość |
|------|---------|
| **ID** | AX-003 |
| **Kategoria** | mass_balance |
| **Treść** | Objętość urobku przeznaczonego na nasyp nie może przekraczać objętości wykopu pomniejszonej o normatywną stratę technologiczną (max 3%) |
| **Przykład naruszenia** | Nasyp 9 800 m³ z wykopu 9 000 m³ — nasyp > wykop bez uzasadnienia pozyskania z innego miejsca |
| **Severity** | CRITICAL |
| **clingo_hint** | `nasyp_bez_zrodla(T) :- nasyp_vol(T,N), wykop_vol(T,W), N > W*1.03, not pozyskanie_zewnetrzne(T).` |
| **Norma** | PN-B-06050:1999, KNR 2-01 |

---

#### AX-004
| Pole | Wartość |
|------|---------|
| **ID** | AX-004 |
| **Kategoria** | mass_balance |
| **Treść** | Przy wymianie gruntu nasypowego warunek: objętość usuniętego gruntu ≥ objętości wymienianego gruntu |
| **Przykład naruszenia** | Wymiana gruntu 500 m³, a usunięcie słabego podłoża wycenione na 300 m³ — brakuje 200 m³ usunięcia |
| **Severity** | CRITICAL |
| **clingo_hint** | `wymiana_niekompletna(T) :- wymiana_gruntu(T,V), usuniecie_gruntu(T,Vu), Vu < V.` |
| **Norma** | PN-S-02205:1998, GDDKiA WT-4 |

---

#### AX-005
| Pole | Wartość |
|------|---------|
| **ID** | AX-005 |
| **Kategoria** | mass_balance |
| **Treść** | Materiał z humusowania (zebranie humusu) musi mieć zdefiniowane miejsce przeznaczenia: składowanie lub ponowne wbudowanie |
| **Przykład naruszenia** | Zebranie humusu 2 000 m³ w pozycji przedmiaru bez pozycji odwozu, składowania lub powrotnego rozłożenia |
| **Severity** | WARNING |
| **clingo_hint** | `humus_bez_przeznaczenia(T) :- zebranie_humusu(T,V), not odwoz_humusu(T,_), not rozlozenie_humusu(T,_).` |
| **Norma** | KNR 2-01 r.1, PN-EN ISO 14688-1 |

---

#### AX-006
| Pole | Wartość |
|------|---------|
| **ID** | AX-006 |
| **Kategoria** | mass_balance |
| **Treść** | Objętość betonu podkładowego/wyrównawczego w dnie wykopu musi być ≤ 5% objętości wykopu fundamentowego |
| **Przykład naruszenia** | Wykop fundamentowy 200 m³, beton podkładowy wyceniony na 50 m³ (25% objętości) — błąd kalkulacyjny |
| **Severity** | WARNING |
| **clingo_hint** | `beton_podkladowy_error(T) :- beton_pod(T,Vb), wykop_fund(T,Vw), Vb > 0.05*Vw.` |
| **Norma** | KNR 2-02, PN-EN 13670 |

---

#### AX-007
| Pole | Wartość |
|------|---------|
| **ID** | AX-007 |
| **Kategoria** | mass_balance |
| **Treść** | Przy robotach w gruntach organicznych (torf, namu³) współczynnik strat po odwodnieniu i konsolidacji wynosi min. 1.15 dla bilans masy nasypowej |
| **Przykład naruszenia** | Nasyp na torfisku 1 000 m³ bez doliczenia osiadań konsolidacyjnych w harmonogramie ilości |
| **Severity** | WARNING |
| **clingo_hint** | `grunt_organiczny_konsolidacja(T) :- typ_gruntu(T,organiczny), nasyp_vol(T,N), not wskaznik_konsolidacji(T,_).` |
| **Norma** | PN-EN 1997-1:2008, EC7 |

---

#### AX-008
| Pole | Wartość |
|------|---------|
| **ID** | AX-008 |
| **Kategoria** | mass_balance |
| **Treść** | Nasyp drogowy kat. A (autostrada, DK): wymagany wskaźnik zagęszczenia Is ≥ 1.00, nasyp kat. B (droga gminna) Is ≥ 0.97 — musi być pozycja na badania zagęszczenia |
| **Przykład naruszenia** | Nasyp autostrady 50 000 m³ bez pozycji kosztorysowej na próby Proctora i sondy VSS |
| **Severity** | WARNING |
| **clingo_hint** | `brak_badan_zageszenia(T) :- kategoria_drogi(T,A), nasyp_vol(T,V), V>0, not badania_proctor(T,_).` |
| **Norma** | GDDKiA WT-4:2010, PN-S-02205 |

---

### KATEGORIA: DRAINAGE (Odwodnienie)

---

#### AX-009
| Pole | Wartość |
|------|---------|
| **ID** | AX-009 |
| **Kategoria** | drainage |
| **Treść** | Wykop o głębokości > 1.5 m musi zawierać pozycję odwodnienia (igłofiltry, pompowanie, drenaż) lub potwierdzenie gruntu suchego z badań |
| **Przykład naruszenia** | Wykop fundamentowy głębokość 2.4 m w terenie zalewowym bez żadnej pozycji odwodnienia |
| **Severity** | CRITICAL |
| **clingo_hint** | `brak_odwodnienia(T) :- glebokos_wykopu(T,G), G>1.5, not pozycja_odwodnienia(T,_), not grunt_suchy_potwierdzony(T).` |
| **Norma** | PN-B-06050:1999 §5.3, BHP Dz.U. 2003 nr 47 poz. 401 |

---

#### AX-010
| Pole | Wartość |
|------|---------|
| **ID** | AX-010 |
| **Kategoria** | drainage |
| **Treść** | Odwodnienie wykopu musi poprzedzać roboty ziemne — brak sekwencji czasowej w harmonogramie jest błędem |
| **Przykład naruszenia** | Harmonogram: Tydzień 1 — wykop, Tydzień 3 — igłofiltry. Kolejność odwrócona. |
| **Severity** | CRITICAL |
| **clingo_hint** | `odwodnienie_po_wykopie(T) :- czas_start(T,odwodnienie,T1), czas_start(T,wykop,T2), T1 > T2.` |
| **Norma** | PN-B-06050:1999, WT GDDKiA |

---

#### AX-011
| Pole | Wartość |
|------|---------|
| **ID** | AX-011 |
| **Kategoria** | drainage |
| **Treść** | Przy obecności warstwy wodonośnej (zwierciadło wody < 2.0 m od dna wykopu): wymagane uszczelnienie ścian lub pompowanie z odwiertu |
| **Przykład naruszenia** | Zwierciadło wody 0.8 m, dno wykopu -1.5 m, brak pozycji na odwiert odwadniający lub ściankę |
| **Severity** | CRITICAL |
| **clingo_hint** | `warstawa_wodnos_niezabezp(T) :- zwierz_wody(T,Zw), dno_wykopu(T,Dw), Zw-Dw < 2.0, not uszczelnienie(T,_), not odwiert_odwad(T,_).` |
| **Norma** | PN-EN 1997-1:2008 Annex B, EC7 |

---

#### AX-012
| Pole | Wartość |
|------|---------|
| **ID** | AX-012 |
| **Kategoria** | drainage |
| **Treść** | Rowy odprowadzające wodę z wykopu muszą być uwzględnione jako odrębna pozycja przy odkrytym terenie > 5 000 m² |
| **Przykład naruszenia** | Roboty ziemne na terenie 8 ha, brak pozycji na rowy odwadniające i sączki |
| **Severity** | WARNING |
| **clingo_hint** | `brak_rowow_odw(T) :- powierzchnia_robot(T,P), P > 5000, not rowy_odwadniajace(T,_).` |
| **Norma** | KNR 2-01 r.4, PN-B-10736:1999 |

---

#### AX-013
| Pole | Wartość |
|------|---------|
| **ID** | AX-013 |
| **Kategoria** | drainage |
| **Treść** | Pompowanie wody z wykopu: wydajność pompy musi pokryć притоk wody z przepuszczalności hydraulicznej gruntu (k > 10⁻⁴ m/s wymaga pompy wydajność min. Q = k × i × A) |
| **Przykład naruszenia** | Grunt piaszczysty k=10⁻³ m/s, powierzchnia wykopu 500 m², dobrana pompa 5 m³/h zamiast min. ~36 m³/h |
| **Severity** | WARNING |
| **clingo_hint** | `pompa_za_mala(T) :- przepuszczalnosc(T,K), K>1e-4, pow_wykopu(T,A), wydajnosc_pompy(T,Q), Q < K*1.0*A*3600.` |
| **Norma** | PN-EN ISO 22282-1, hydrogeologia Darcy'ego |

---

#### AX-014
| Pole | Wartość |
|------|---------|
| **ID** | AX-014 |
| **Kategoria** | drainage |
| **Treść** | Czas pracy pompowni nie może być krótszy niż czas trwania robot ziemnych + 14 dni po ich zakończeniu (konsolidacja) |
| **Przykład naruszenia** | Harmonogram pompowania 30 dni, roboty ziemne 45 dni — pompowanie kończy się przed robotami |
| **Severity** | WARNING |
| **clingo_hint** | `pompowanie_za_krotkie(T) :- czas_trwania(T,pompowanie,Tp), czas_trwania(T,roboty_ziemne,Tr), Tp < Tr+14.` |
| **Norma** | PN-B-06050:1999, praktyka inżynierska |

---

### KATEGORIA: COMPACTION (Zagęszczenie)

---

#### AX-015
| Pole | Wartość |
|------|---------|
| **ID** | AX-015 |
| **Kategoria** | compaction |
| **Treść** | Wskaźnik zagęszczenia Is ≥ 1.00 dla podłoża drogi klasy GP i wyżej; Is ≥ 0.97 dla dróg G i Z; Is ≥ 0.95 dla lokalnych (L, D) |
| **Przykład naruszenia** | Droga ekspresowa, nasyp wyceniony bez warstw zagęszczenia i kontroli VSS (sonda VSS wg BN-77/8931-12) |
| **Severity** | CRITICAL |
| **clingo_hint** | `brak_zageszenia_droga(T) :- klasa_drogi(T,C), wymag_Is(C,Is), not zageszenie_Is(T,Is2), Is2 < Is.` |
| **Norma** | GDDKiA WT-4:2010 tab. 1, PN-S-02205:1998 §8 |

---

#### AX-016
| Pole | Wartość |
|------|---------|
| **ID** | AX-016 |
| **Kategoria** | compaction |
| **Treść** | Maksymalna grubość warstwy zagęszczanej: grunt sypki 30 cm, grunt spoistny 20 cm (walec wibracyjny) — zbyt gruba warstwa to błąd pozycji przedmiaru |
| **Przykład naruszenia** | Nasyp 5 000 m³ z gruntu gliniastego, brak podziału na warstwy ≤ 20 cm w opisie technologicznym |
| **Severity** | WARNING |
| **clingo_hint** | `warstwa_za_gruba(T) :- typ_gruntu(T,spoistY), grubosc_warstwy(T,G), G > 0.20.` |
| **Norma** | PN-S-02205:1998 §8.4, KNR 2-01 tab. 0401 |

---

#### AX-017
| Pole | Wartość |
|------|---------|
| **ID** | AX-017 |
| **Kategoria** | compaction |
| **Treść** | Zagęszczenie gruntu pod fundamentem: Is ≥ 1.00 (budynki mieszkalne ≥ 3 kondygnacji), Is ≥ 0.97 (1-2 kondygnacje) — wymagane badania |
| **Przykład naruszenia** | Budynek wielorodzinny 6-kondygnacyjny, nasyp wyrównawczy 800 m³ bez pozycji badań Proctora |
| **Severity** | CRITICAL |
| **clingo_hint** | `brak_zageszenia_budynek(T) :- kondygnacje(T,K), K>=3, nasyp_pod_fund(T,V), V>0, not badania_proctor(T,_).` |
| **Norma** | PN-B-03020:1981, PN-EN 1997-1 |

---

#### AX-018
| Pole | Wartość |
|------|---------|
| **ID** | AX-018 |
| **Kategoria** | compaction |
| **Treść** | Wilgotność optymalna gruntu (wopt ± 2%) — przy materiale gruntowym spoza lokalizacji wymagana analiza wilgotności w kosztorysie |
| **Przykład naruszenia** | Dowieziony grunt z odkrywki 30 km, brak pozycji na regulację wilgotności (nawilżanie/osuszanie) |
| **Severity** | INFO |
| **clingo_hint** | `brak_korekcji_wilgotnosci(T) :- grunt_zewnetrzny(T,_), not regulacja_wilgotnosci(T,_).` |
| **Norma** | PN-S-02205:1998, BN-64/8931-01 |

---

#### AX-019
| Pole | Wartość |
|------|---------|
| **ID** | AX-019 |
| **Kategoria** | compaction |
| **Treść** | Nasyp budowlany > 3 m wysokości: wymagane próby sondą dynamiczną (DPL/DPM) lub VSS co 500 m² — musi być pozycja w kosztorysie |
| **Przykład naruszenia** | Nasyp 4.5 m, powierzchnia 10 000 m², brak 20 prób VSS (koszt ok. 800–1 200 PLN/próba) |
| **Severity** | WARNING |
| **clingo_hint** | `brak_sond_nasypHigh(T) :- wys_nasypu(T,H), H>3.0, pow_nasypu(T,A), not sonda_vss(T,_).` |
| **Norma** | GDDKiA WT-4:2010, BN-77/8931-12 |

---

#### AX-020
| Pole | Wartość |
|------|---------|
| **ID** | AX-020 |
| **Kategoria** | compaction |
| **Treść** | Zastosowanie wibrozagęszczarki płytowej jest niewystarczające dla gruntów spoistych (glina, ił) > 15 cm — wymagany walec lub ubicak |
| **Przykład naruszenia** | Grunt: glina ciężka, warstwa 25 cm, w pozycji sprzętu tylko zagęszczarka płytowa 200 kg |
| **Severity** | WARNING |
| **clingo_hint** | `zly_sprzet_zageszenia(T) :- typ_gruntu(T,glina), grubosc_warstwy(T,G), G>0.15, sprzet_zageszenia(T,plytowa).` |
| **Norma** | PN-S-02205:1998, KNR 2-01 kom. |

---

### KATEGORIA: SEQUENCE (Kolejność Robót)

---

#### AX-021
| Pole | Wartość |
|------|---------|
| **ID** | AX-021 |
| **Kategoria** | sequence |
| **Treść** | Kolejność bezwzględna: humusowanie → odwodnienie → wykop fundamentowy → zasypka. Nasyp NIE może poprzedzać wykopu w tej samej warstwie terenu |
| **Przykład naruszenia** | Harmonogram: Tydzień 2 — nasyp wyrównawczy, Tydzień 5 — wykop fundamentów. Nasyp zasypuje teren przed wykopem. |
| **Severity** | CRITICAL |
| **clingo_hint** | `zla_kolejnosc_nasyp_wykop(T,L) :- warstwa(T,L), czas_start(T,nasyp(L),T1), czas_start(T,wykop(L),T2), T1 < T2.` |
| **Norma** | PN-B-06050:1999 §5.1, logika budowlana |

---

#### AX-022
| Pole | Wartość |
|------|---------|
| **ID** | AX-022 |
| **Kategoria** | sequence |
| **Treść** | Zebranie warstwy humusu musi poprzedzać wszelkie roboty ziemne wykopowe i nasypowe |
| **Przykład naruszenia** | Przedmiar: Poz. 1 — wykop pod fundament, Poz. 12 — zebranie humusu. Kolejność niezgodna. |
| **Severity** | WARNING |
| **clingo_hint** | `humus_po_robotach(T) :- numer_pozycji(T,humus,N1), numer_pozycji(T,wykop,N2), N1 > N2.` |
| **Norma** | PN-B-06050:1999 §4.1, KNR 2-01 r.1 |

---

#### AX-023
| Pole | Wartość |
|------|---------|
| **ID** | AX-023 |
| **Kategoria** | sequence |
| **Treść** | Ścianka szczelna lub obudowa wykopu musi być wbudowana PRZED rozpoczęciem wykopu gdy nachylenie skarp < 1:1 lub głębokość > 2.0 m w terenie zurbanizowanym |
| **Przykład naruszenia** | Wykop 3.0 m w zabudowie miejskiej, ścianka Larssena w pozycji po wykopie bez uzasadnienia |
| **Severity** | CRITICAL |
| **clingo_hint** | `scianka_po_wykopie(T) :- teren(T,zurbanizowany), glebokos_wykopu(T,G), G>2.0, czas_start(T,scianka,T1), czas_start(T,wykop,T2), T1 > T2.` |
| **Norma** | PN-B-06050:1999 §6.2, BHP Dz.U. 2003 nr 47 |

---

#### AX-024
| Pole | Wartość |
|------|---------|
| **ID** | AX-024 |
| **Kategoria** | sequence |
| **Treść** | Zasypka wykopów instalacyjnych musi następować po próbie ciśnieniowej instalacji, nie przed |
| **Przykład naruszenia** | Harmonogram: Tydzień 3 — zasypka, Tydzień 5 — próba ciśnieniowa wodociągu. Zasypka przed próbą. |
| **Severity** | CRITICAL |
| **clingo_hint** | `zasypka_przed_proba(T) :- czas_koniec(T,zasypka_inst,T1), czas_start(T,proba_cisn,T2), T1 < T2.` |
| **Norma** | PN-EN 805:2002 (wodociągi), PN-EN 1610 (kanalizacja) |

---

#### AX-025
| Pole | Wartość |
|------|---------|
| **ID** | AX-025 |
| **Kategoria** | sequence |
| **Treść** | Roboty palowe (pale fundamentowe) muszą poprzedzać wykop do poziomu fundamentów — pale nie mogą być wykonywane z dna wykopu jeśli przedmiar tego nie zakłada |
| **Przykład naruszenia** | Pale CFA z dna wykopu -3.0 m, w harmonogramie pale przed wykopem — sprzeczność z technologią |
| **Severity** | WARNING |
| **clingo_hint** | `pale_w_zlej_fazie(T) :- technologia_pali(T,cfa_z_powierzchni), czas_start(T,pale,T1), czas_start(T,wykop,T2), T1 > T2.` |
| **Norma** | PN-EN 12699:2015 (pale przemieszczeniowe) |

---

#### AX-026
| Pole | Wartość |
|------|---------|
| **ID** | AX-026 |
| **Kategoria** | sequence |
| **Treść** | Geosiatka wzmacniająca nasyp: montaż musi poprzedzać nasyp warstwy, której dotyczy — nie może być po |
| **Przykład naruszenia** | Poz. 1 — nasyp warstwa 1 (30 cm), Poz. 3 — geosiatka warstwa 1. Geosiatka po nasyp |
| **Severity** | WARNING |
| **clingo_hint** | `geosiatka_po_nasyp(T,W) :- warstwa(T,W), poz_nr(T,nasyp(W),N1), poz_nr(T,geosiatka(W),N2), N2 > N1.` |
| **Norma** | PN-EN 13251:2016, zalecenia producenta |

---

### KATEGORIA: SAFETY (Bezpieczeństwo)

---

#### AX-027
| Pole | Wartość |
|------|---------|
| **ID** | AX-027 |
| **Kategoria** | safety |
| **Treść** | Nachylenie skarp wykopu niezabezpieczonego: kat. I–II max 1:0.5, kat. III max 1:1, kat. IV min 1:1.5 — przekroczenie bez obudowy = błąd krytyczny |
| **Przykład naruszenia** | Gleba kat. IV (nasyp luźny), projektowana skarpa 1:0.75 bez obudowy — grozi obsunięciem |
| **Severity** | CRITICAL |
| **clingo_hint** | `niebezpieczna_skarpa(T) :- kategoria_gruntu(T,IV), nachylenie_skarpy(T,N), N > 0.667, not obudowa_wykopu(T,_).` |
| **Norma** | PN-B-06050:1999 tab. 3, Rozp. Min. Inf. 2003 §72 |

---

#### AX-028
| Pole | Wartość |
|------|---------|
| **ID** | AX-028 |
| **Kategoria** | safety |
| **Treść** | Przy wykopie w pobliżu istniejących fundamentów (d < 3×głębokość wykopu): wymagana analiza stateczności i ewentualnie podbicie |
| **Przykład naruszenia** | Nowy wykop 2.5 m głębokości 1.5 m od istniejącego budynku bez pozycji na monitoring i ewentualne podchody |
| **Severity** | CRITICAL |
| **clingo_hint** | `wykop_blisko_fundamentu(T) :- glebokos_wykopu(T,G), dystans_fundament(T,D), D < 3*G, not analiza_statecznosci(T,_).` |
| **Norma** | PN-B-06050:1999 §6.4, EC7 Annex H |

---

#### AX-029
| Pole | Wartość |
|------|---------|
| **ID** | AX-029 |
| **Kategoria** | safety |
| **Treść** | Przy robotach w pobliżu podziemnej infrastruktury (gaz, energia): wymagana inwentaryzacja, oznaczenie i ręczne odkrycie — brak tych pozycji = ryzyko |
| **Przykład naruszenia** | Wykop w pasie drogi miejskiej 200 m bez pozycji na ręczne odkrycie mediów i nadzór gestorów |
| **Severity** | CRITICAL |
| **clingo_hint** | `brak_odkrycia_mediow(T) :- teren_zurbanizowany(T), dlugosc_wykopu(T,L), L>50, not reczne_odkrycie(T,_).` |
| **Norma** | Ustawa Prawo Budowlane art. 36a, ZUDP |

---

#### AX-030
| Pole | Wartość |
|------|---------|
| **ID** | AX-030 |
| **Kategoria** | safety |
| **Treść** | Wykop o głębokości > 4.0 m: obowiązkowe zabezpieczenie przez uprawnionego konstruktora — brak projektu obudowy = błąd formalny |
| **Przykład naruszenia** | Wykop 5.5 m dla zbiornika retencyjnego bez pozycji obudowy i bez odwołania do projektu obudowy |
| **Severity** | CRITICAL |
| **clingo_hint** | `wykop_gleboki_bez_projektu(T) :- glebokos_wykopu(T,G), G>4.0, not projekt_obudowy(T,_).` |
| **Norma** | Rozp. Min. Inf. 2003 §72 ust. 2, Prawo Budowlane |

---

#### AX-031
| Pole | Wartość |
|------|---------|
| **ID** | AX-031 |
| **Kategoria** | safety |
| **Treść** | Prace w wykopie o szerokości < 0.8 m (rów): wymagane deskowanie ciągłe lub grodzice — brak = naruszenie BHP |
| **Przykład naruszenia** | Rów kablowy 0.6 m szerokości, głębokość 1.8 m, bez obudowy szalunkowej |
| **Severity** | CRITICAL |
| **clingo_hint** | `row_wąski_bez_deskowania(T) :- szerokosc_wykopu(T,S), S<0.8, glebokos_wykopu(T,G), G>1.2, not deskowanie(T,_).` |
| **Norma** | BHP Dz.U. 2003 nr 47 poz. 401 §84 |

---

#### AX-032
| Pole | Wartość |
|------|---------|
| **ID** | AX-032 |
| **Kategoria** | safety |
| **Treść** | Odległość składowania urobku od krawędzi wykopu ≥ 1.0 m lub 1/3 głębokości wykopu (większa wartość) — check geometryczny |
| **Przykład naruszenia** | Urobek składowany 0.5 m od krawędzi wykopu 3.0 m — wymagane min. 1.0 m |
| **Severity** | WARNING |
| **clingo_hint** | `urobek_za_blisko(T) :- dystans_urobek(T,D), glebokos_wykopu(T,G), min_dist(G,Dmin), D < Dmin.` |
| **Norma** | BHP Dz.U. 2003 nr 47 §76 |

---

### KATEGORIA: COST_RATIO (Relacje Kosztowe)

---

#### AX-033
| Pole | Wartość |
|------|---------|
| **ID** | AX-033 |
| **Kategoria** | cost_ratio |
| **Treść** | Koszt odwozu 1 m³ urobku nie może przekraczać 150% mediany rynkowej dla danego regionu (orientacyjnie 25–60 PLN/m³ w 2026) |
| **Przykład naruszenia** | Wywóz urobku wyceniony 120 PLN/m³ dla trasy 5 km — rynkowe maksimum to ~60 PLN/m³ |
| **Severity** | WARNING |
| **clingo_hint** | `przeszacowany_wywoz(T,P) :- koszt_jednostkowy(T,P,K), typ_pozycji(P,wywoz_urobku), mediana_rynkowa(wywoz,M), K > M*1.5.` |
| **Norma** | SEKOCENBUD Q1-2026, BIM Cost DB |

---

#### AX-034
| Pole | Wartość |
|------|---------|
| **ID** | AX-034 |
| **Kategoria** | cost_ratio |
| **Treść** | Relacja: koszty sprzętu / koszty materiałów w robotach ziemnych powinna wynosić 65–80% sprzętu i 5–15% materiałów (normy KNR) |
| **Przykład naruszenia** | Kosztorys: materiały 60%, sprzęt 20% — odwrócona proporcja sugeruje błąd kwalifikacji kosztów |
| **Severity** | WARNING |
| **clingo_hint** | `zla_proporcja_kosztor(T) :- koszt_sprzetu(T,Ks), koszt_materialow(T,Km), koszt_razem(T,Kr), Ks/Kr < 0.5.` |
| **Norma** | KNR 2-01, KSNR, praktyka branżowa |

---

#### AX-035
| Pole | Wartość |
|------|---------|
| **ID** | AX-035 |
| **Kategoria** | cost_ratio |
| **Treść** | Koszt 1 m³ wykopu koparką podsiębiernną: kat. I–II: 8–18 PLN/m³; kat. III: 18–30 PLN/m³; kat. IV: 30–55 PLN/m³ (2026). Odchylenie >40% = flaga |
| **Przykład naruszenia** | Wykop kat. II wyceniony 85 PLN/m³ przy medianie 13 PLN/m³ — zawyżenie 6× |
| **Severity** | WARNING |
| **clingo_hint** | `przeszacowany_wykop(T,P) :- koszt_jed(T,P,K), kat_gruntu(T,P,Cat), zakres_normatywny(Cat,Min,Max), K > Max*1.4.` |
| **Norma** | SEKOCENBUD, KNR 2-01 |

---

#### AX-036
| Pole | Wartość |
|------|---------|
| **ID** | AX-036 |
| **Kategoria** | cost_ratio |
| **Treść** | Narzut kosztów pośrednich (Kp) dla robót ziemnych: normatywnie 50–65% od R+S. Wartości poza zakresem 30–100% wymagają uzasadnienia |
| **Przykład naruszenia** | Kp = 8% od R+S dla wykopu maszynowego — zbyt niski, sugeruje pominięcie kosztów |
| **Severity** | INFO |
| **clingo_hint** | `kp_poza_normą(T) :- narzut_kp(T,Kp), (Kp < 30 ; Kp > 100).` |
| **Norma** | OWEOB "Orgbud" 2026, SEKOCENBUD |

---

#### AX-037
| Pole | Wartość |
|------|---------|
| **ID** | AX-037 |
| **Kategoria** | cost_ratio |
| **Treść** | Zysk (Z) w robotach ziemnych: normatywnie 5–12%. Zysk < 3% może sugerować błąd lub dumping; > 20% = zawyżenie |
| **Przykład naruszenia** | Oferta: Z = 1.2% przy rynkowym minimum 5% — podejrzenie dumpingu lub błędu obliczeniowego |
| **Severity** | INFO |
| **clingo_hint** | `zysk_poza_norm(T) :- zysk_procent(T,Z), (Z < 3 ; Z > 20).` |
| **Norma** | OWEOB 2026, praktyka przetargowa |

---

#### AX-038
| Pole | Wartość |
|------|---------|
| **ID** | AX-038 |
| **Kategoria** | cost_ratio |
| **Treść** | Robocizna w robotach ziemnych maszynowych: max 15% kosztów bezpośrednich. Wartość > 25% = błąd kategoryzacji lub brak sprzętu |
| **Przykład naruszenia** | Robocizna 40% kosztów bezpośrednich wykopu maszynowego — ewidentny błąd: brakują kalkulacje sprzętu |
| **Severity** | WARNING |
| **clingo_hint** | `za_duzo_robocizny(T) :- udzial_robocizny(T,R), R > 25, typ_robot(T,maszynowe).` |
| **Norma** | KNR 2-01 kalkulacje normatywne |

---

#### AX-039
| Pole | Wartość |
|------|---------|
| **ID** | AX-039 |
| **Kategoria** | cost_ratio |
| **Treść** | Suma kosztów pozycji dodatkowych (badania, obsługa geodezyjna, nadzory) nie może przekraczać 8% wartości robót ziemnych podstawowych |
| **Przykład naruszenia** | Roboty ziemne 500 000 PLN, obsługa geodezyjna wyceniona na 60 000 PLN (12%) — rażące zawyżenie |
| **Severity** | INFO |
| **clingo_hint** | `koszty_dodatkowe_za_high(T) :- koszt_dodatkowy(T,Kd), koszt_podstawowy(T,Kp), Kd > 0.08*Kp.` |
| **Norma** | branżowe normy STO |

---

#### AX-040
| Pole | Wartość |
|------|---------|
| **ID** | AX-040 |
| **Kategoria** | cost_ratio |
| **Treść** | Całkowity koszt robót ziemnych w stosunku do wartości inwestycji: dla budownictwa ogólnego 8–15%; dla drogownictwa 20–35%; dla hydrotechniki 30–50% |
| **Przykład naruszenia** | Budynek biurowy 10 mln PLN, roboty ziemne wycenione na 3.2 mln PLN (32%) — przekracza typowe 15% |
| **Severity** | WARNING |
| **clingo_hint** | `udzial_rob_ziem_za_high(T) :- typ_inwestycji(T,budynek), koszt_ziemnych(T,Kz), wartosc_inwest(T,Wi), Kz/Wi > 0.15.` |
| **Norma** | SEKOCENBUD GUS, statystyka przetargów |

---

### KATEGORIA: MIXED / DODATKOWE

---

#### AX-041
| Pole | Wartość |
|------|---------|
| **ID** | AX-041 |
| **Kategoria** | mass_balance |
| **Treść** | Przy terenie pochyłym (spadek > 5%): objętość wykopu obliczona metodą przekrojów poprzecznych musi być zweryfikowana przez siatki wysokościowe ±3% |
| **Przykład naruszenia** | Nasyp drogowy na terenie górskim, objętość z profili ≠ objętości z TIN modelu terenu — różnica 18% |
| **Severity** | WARNING |
| **clingo_hint** | `roznica_obj_profil_tin(T) :- obj_profile(T,Op), obj_tin(T,Ot), abs(Op-Ot)/Ot > 0.03.` |
| **Norma** | PN-G-09010, GIS/BIM standard |

---

#### AX-042
| Pole | Wartość |
|------|---------|
| **ID** | AX-042 |
| **Kategoria** | drainage |
| **Treść** | Przy montażu drenażu opaskowego: geowłóknina otulająca drenaż musi być uwzględniona jako odrębna pozycja (min. 0.5 m²/mb drenażu) |
| **Przykład naruszenia** | Drenaż opaskowy 120 mb, brak pozycji na geowłókninę filtracyjną (norm. 60–70 m²) |
| **Severity** | WARNING |
| **clingo_hint** | `brak_geowlok_dren(T) :- dlugosc_drenazu(T,L), L>0, not geowloknina_dren(T,_).` |
| **Norma** | PN-EN 13252:2016, KNR 2-01 r.4 |

---

#### AX-043
| Pole | Wartość |
|------|---------|
| **ID** | AX-043 |
| **Kategoria** | sequence |
| **Treść** | Badania geotechniczne (wiercenia, sondowania) muszą poprzedzać wszelkie roboty ziemne — brak lub późniejszy termin to błąd planowania |
| **Przykład naruszenia** | Harmonogram: Miesiąc 1 — roboty ziemne, Miesiąc 3 — wiercenia geotechniczne |
| **Severity** | CRITICAL |
| **clingo_hint** | `brak_geotechniki_przed(T) :- czas_start(T,roboty_ziemne,T1), czas_start(T,geotechnika,T2), T2 >= T1.` |
| **Norma** | PN-EN 1997-2:2008 (EC7-2), Prawo Budowlane |

---

#### AX-044
| Pole | Wartość |
|------|---------|
| **ID** | AX-044 |
| **Kategoria** | safety |
| **Treść** | Przy robotach ziemnych w pobliżu linii kolejowej (< 20 m od osi toru): wymagane zamknięcie torowe lub nadzór PKP PLK — brak pozycji kosztorysowej |
| **Przykład naruszenia** | Wykop 15 m od toru PKP bez pozycji na nadzór gestora i opłatę za zamknięcie torowe |
| **Severity** | CRITICAL |
| **clingo_hint** | `brak_nadzoru_pkp(T) :- dystans_tor(T,D), D<20, not nadzor_pkp(T,_).` |
| **Norma** | Ustawa o transporcie kolejowym, Rozp. MTiGM 1998 |

---

#### AX-045
| Pole | Wartość |
|------|---------|
| **ID** | AX-045 |
| **Kategoria** | cost_ratio |
| **Treść** | Stawka pracy koparki gąsienicowej 20–30 t (2026): 250–380 PLN/MG. Odchylenie >50% = flaga |
| **Przykład naruszenia** | Koparka 25 t wyceniona 780 PLN/MG — rażące zawyżenie (max normatywny ~570 PLN/MG) |
| **Severity** | WARNING |
| **clingo_hint** | `przeszacowana_koparka(T,P) :- stawka_maszyny(T,P,koparka_25t,S), S > 570.` |
| **Norma** | SEKOCENBUD BMSR Q1-2026 |

---

#### AX-046
| Pole | Wartość |
|------|---------|
| **ID** | AX-046 |
| **Kategoria** | compaction |
| **Treść** | Wilgotność gruntu do zagęszczenia nasypów ≥ 2% powyżej granicy skurczliwości Ws — grunt przesuszony wymaga nawilżania |
| **Przykład naruszenia** | Piasek gliniasty w suchym lecie, wilgotność naturalna wn = 3%, wopt = 10% — brak pozycji nawilżania |
| **Severity** | INFO |
| **clingo_hint** | `grunt_przesuszony_brak_nawilz(T) :- wilgotnosc_naturalna(T,Wn), wopt(T,Wo), Wn < Wo-3, not nawilzanie(T,_).` |
| **Norma** | PN-S-02205:1998 §8.3 |

---

#### AX-047
| Pole | Wartość |
|------|---------|
| **ID** | AX-047 |
| **Kategoria** | mass_balance |
| **Treść** | Grunt skażony (kategoria zanieczyszczeń wg Rozp. MŚ): wywóz musi być ujęty w specjalnej pozycji z kodem odpadów 17 05 03* (grunt z substancjami niebezpiecznymi) |
| **Przykład naruszenia** | Teren poprzemysłowy, wywóz gruntu bez wydzielenia gruntu skażonego i kodu odpadów — naruszenie ustawy o odpadach |
| **Severity** | CRITICAL |
| **clingo_hint** | `skazony_grunt_bez_kodu(T) :- teren_poprzemyslowy(T), not kod_odpadow(T,"17 05 03*").` |
| **Norma** | Rozp. MŚ 2016 (Dz.U. 2016 poz. 1395), Ustawa o odpadach 2012 |

---

#### AX-048
| Pole | Wartość |
|------|---------|
| **ID** | AX-048 |
| **Kategoria** | drainage |
| **Treść** | Szczelność zbiornika (basen, zbiornik retencyjny): wykop musi zawierać pozycję uszczelnienia dna (bentomata, folia HDPE) przed wypełnieniem |
| **Przykład naruszenia** | Zbiornik retencyjny 5 000 m³, wykop wyceniony, brak pozycji na geomembranę lub uszczelnienie |
| **Severity** | CRITICAL |
| **clingo_hint** | `zbiornik_bez_uszczelnienia(T) :- typ_obiektu(T,zbiornik), not uszczelnienie_dna(T,_).` |
| **Norma** | PN-EN 13491:2018 (geomembrany), WT GDDKiA |

---

#### AX-049
| Pole | Wartość |
|------|---------|
| **ID** | AX-049 |
| **Kategoria** | cost_ratio |
| **Treść** | Transport urobku: koszt = (stawka pojazdu × czas załadunku + stawka km × 2 × odległość) / ładowność. Niezgodność z parametrami pojazdu > 30% = flaga |
| **Przykład naruszenia** | Samochód 10 t, trasa 20 km, wycenione 200 PLN/kurs — rynkowo ~85–120 PLN/kurs przy stawce 4 PLN/km |
| **Severity** | WARNING |
| **clingo_hint** | `nieracjonalny_transport(T,P) :- koszt_kursu(T,P,K), odleglosc(T,P,L), stawka_km(4), K > 4*2*L*1.3+50.` |
| **Norma** | SEKOCENBUD BMSR, rynek przewoźników 2026 |

---

#### AX-050
| Pole | Wartość |
|------|---------|
| **ID** | AX-050 |
| **Kategoria** | sequence |
| **Treść** | Roboty ziemne zimowe (temperatura < 0°C): wymagane pozycje na podgrzewanie gruntu lub zabezpieczenie termiczne nasypów — brak = błąd technologiczny |
| **Przykład naruszenia** | Termin robót: styczeń–marzec w Polsce centralnej, brak pozycji na ogrzewanie gruntu i folie termiczne |
| **Severity** | WARNING |
| **clingo_hint** | `roboty_zimowe_bez_zabezp(T) :- miesiac_robot(T,M), M<=3, not ogrzewanie_gruntu(T,_), not folia_termiczna(T,_).` |
| **Norma** | PN-B-06050:1999 §9, KNR 2-01 r.9 |

---

## CZĘŚĆ 2: TAKSONOMIA CPV — PEŁNA MAPA DLA ROBÓT ZIEMNYCH

### 2.1 Główne kody CPV — Roboty Ziemne

| Kod CPV | Nazwa PL | Opis robót | Typowe stawki 2026 (PLN/m³) |
|---------|----------|------------|----------------------------|
| **45112000-5** | Roboty w zakresie usuwania gleby | Wykopy, zbieranie humusu, nasypy, transport urobku, rekultywacja | 12–55 PLN/m³ |
| **45111000-8** | Roboty w zakresie burzenia, rozbiórki i robót ziemnych | Rozbiórki istniejących konstrukcji + towarzyszące roboty ziemne | 25–180 PLN/m³ |
| **45112710-5** | Roboty w zakresie kształtowania terenu | Niwelacja, modelowanie skarp, kształtowanie zieleni, nasypy ozdobne | 18–45 PLN/m³ |
| **45112500-0** | Roboty ziemne | Wykopy ogólnobudowlane, roboty przygotowawcze | 10–40 PLN/m³ |

---

### 2.2 Rozwinięcie podkodów CPV 45112000-5

| Podkod CPV | Nazwa PL | Typowe roboty | Stawka (PLN) | Jednostka |
|------------|----------|---------------|-------------|-----------|
| **45112100-6** | Roboty w zakresie kopania rowów | Rowy odwadniające, rowy fundamentowe, kanały otwarte | 35–90 | PLN/m |
| **45112200-7** | Roboty w zakresie usuwania gleby ornej | Zdjęcie warstwy humusu, odwóz i składowanie | 8–22 | PLN/m² |
| **45112210-0** | Roboty w zakresie usuwania gleby ornej dla terenów sportowych | Humusowanie obiektów sportowych, pielęgnacja | 25–55 | PLN/m² |
| **45112300-8** | Roboty ziemne na obszarach podmokłych | Wykopy na terenach bagiennych, pale drewniane wstępne | 55–150 | PLN/m³ |
| **45112400-9** | Roboty ziemne wymagające wzmocnienia | Pale, kolumny, wibrokompakcja, jet grouting | 120–800 | PLN/mb |
| **45112420-5** | Roboty w zakresie wzmacniania podłoża dróg | Wzmocnienie podłoża (kolumny DSM, geosiatki) | 45–180 | PLN/m² |
| **45112440-1** | Roboty w zakresie kształtowania terenu dla celów sportu | Modelowanie terenu boisk, stoków narciarskich | 30–70 | PLN/m³ |
| **45112450-4** | Roboty w zakresie rewitalizacji terenów zdegradowanych | Rekultywacja terenów poprzemysłowych | 80–400 | PLN/m² |
| **45112500-0** | Roboty ziemne ogólnobudowlane | Wykopy fundamentowe, zasypki | 15–50 | PLN/m³ |
| **45112600-1** | Nasypy i odkłady | Nasypy drogowe, kolejowe, wały przeciwpowodziowe | 20–55 | PLN/m³ |
| **45112700-2** | Roboty w zakresie kształtowania terenu | Niwelacja terenu, plantowanie, profilowanie | 10–30 | PLN/m² |
| **45112710-5** | Kształtowanie terenów zielonych | Modelowanie skarp zieleni, humusowanie zboczy | 18–45 | PLN/m² |
| **45112720-8** | Roboty w zakresie kształtowania parków i ogrodów | Parki publiczne, ogrody zabytkowe | 35–120 | PLN/m² |
| **45112730-1** | Roboty w zakresie kształtowania placów zabaw | Place zabaw, tereny rekreacyjne | 40–150 | PLN/m² |
| **45112740-4** | Roboty w zakresie rekultywacji | Biologiczna rekultywacja gruntów | 25–80 | PLN/m² |

---

### 2.3 Rozwinięcie CPV 45111000-8 (Burzenie i Rozbiórka)

| Podkod CPV | Nazwa PL | Typowe roboty | Stawka 2026 |
|------------|----------|---------------|-------------|
| **45111100-9** | Roboty w zakresie burzenia | Rozbiórka budynków, obiektów inżynierskich | 50–300 PLN/m³ |
| **45111200-0** | Roboty w zakresie przygotowania terenu | Wycinka drzew, usunięcie krzewów, karczowanie | 5–35 PLN/m² |
| **45111210-3** | Roboty ziemne i wykopaliska | Wykopaliska archeologiczne + towarzyszące roboty ziemne | 80–500 PLN/m² |
| **45111213-4** | Roboty w zakresie osuszania terenu | Melioracje, drenaże odwadniające | 25–90 PLN/mb |
| **45111220-6** | Roboty w zakresie usuwania kamieni | Usuwanie głazów, skał, korzeni | 40–180 PLN/m³ |
| **45111230-9** | Roboty w zakresie stabilizacji gruntu | Stabilizacja cementem, wapnem | 35–85 PLN/m² |
| **45111240-2** | Drenaż terenu | Systemy drenarskie, drenaż opaskowy | 120–350 PLN/mb |
| **45111250-5** | Roboty w zakresie przygotowania terenu dla obiektów sportowych | Przygotowanie terenu pod obiekty sportowe | 20–60 PLN/m² |
| **45111290-7** | Roboty przygotowawcze — inne | Prace różne przygotowawcze | zmienne |
| **45111300-1** | Roboty rozbiórkowe | Rozbiórki selektywne z odzyskiem materiałów | 30–200 PLN/m³ |

---

### 2.4 Powiązane kody CPV — Specjalistyczne Roboty Ziemne

| Kod CPV | Nazwa PL | Uwagi |
|---------|----------|-------|
| **45221110-6** | Budowa mostów | Most z robotami ziemnymi przyczółków |
| **45221112-0** | Budowa wiaduktów | Roboty ziemne nasypu drogowego |
| **45231100-6** | Roboty budowlane (rurociągi) | Rowy dla rurociągów |
| **45232130-2** | Roboty budowlane (kanalizacja deszczowa) | Wykopy rowów drenażowych |
| **45233120-6** | Roboty w zakresie budowy dróg | Nasypy drogowe, koryta |
| **45240000-1** | Budowa obiektów inżynierii wodnej | Zapory, wały — roboty ziemne dominują |

---

## CZĘŚĆ 3: WZORZEC KOSZTORYSU — TOP-30 POZYCJI KOSZTORYSOWYCH

### 3.1 Tabela Pozycji Kosztorysowych (KNR 2-01)

| Lp | Kod KNR | Opis pozycji kosztorysowej | Jm | Zakres ilości | Cena jm 2026 [PLN] |
|----|---------|----------------------------|----|----------------|---------------------|
| 1 | KNR 2-01 0112-01 | Zdjęcie warstwy humusu gr. 15 cm — mechanicznie | m² | 500–50 000 | 3,50–7,00 |
| 2 | KNR 2-01 0112-02 | Zdjęcie warstwy humusu gr. 20 cm — mechanicznie | m² | 500–50 000 | 4,80–9,00 |
| 3 | KNR 2-01 0114-01 | Odwóz humusu na odległość do 10 km | m³ | 100–10 000 | 25–45 |
| 4 | KNR 2-01 0120-01 | Wykop koparką kat. I-II (odkład) | m³ | 100–100 000 | 8–18 |
| 5 | KNR 2-01 0120-02 | Wykop koparką kat. III (odkład) | m³ | 100–50 000 | 18–30 |
| 6 | KNR 2-01 0120-03 | Wykop koparką kat. IV (odkład) | m³ | 50–20 000 | 30–55 |
| 7 | KNR 2-01 0121-01 | Wykop ręczny kat. I-II (wąskie wykopy) | m³ | 5–200 | 85–180 |
| 8 | KNR 2-01 0121-03 | Wykop ręczny kat. III (wąskie, trudny dostęp) | m³ | 5–100 | 150–280 |
| 9 | KNR 2-01 0302-01 | Odwóz urobku samochodem 10 t na 5 km | m³ | 50–50 000 | 18–30 |
| 10 | KNR 2-01 0302-02 | Odwóz urobku samochodem 10 t na 10 km | m³ | 50–50 000 | 28–45 |
| 11 | KNR 2-01 0302-04 | Odwóz urobku samochodem 10 t na 20 km | m³ | 50–30 000 | 40–60 |
| 12 | KNR 2-01 0401-01 | Nasyp z gruntu kat. I-II (mechanicznie) | m³ | 100–200 000 | 12–22 |
| 13 | KNR 2-01 0401-02 | Nasyp z gruntu kat. III (mechanicznie) | m³ | 100–100 000 | 20–35 |
| 14 | KNR 2-01 0402-01 | Zagęszczenie nasypu walcem wibracyjnym | m³ | 100–200 000 | 8–16 |
| 15 | KNR 2-01 0402-02 | Zagęszczenie nasypu ubicakiem (ciasne miejsca) | m³ | 10–1 000 | 25–55 |
| 16 | KNR 2-01 0501-01 | Profilowanie i zagęszczenie podłoża gruntowego | m² | 200–50 000 | 4–10 |
| 17 | KNR 2-01 0502-01 | Kształtowanie skarp | m² | 50–20 000 | 6–15 |
| 18 | KNR 2-01 0503-01 | Humusowanie skarp gr. 5 cm | m² | 50–20 000 | 8–20 |
| 19 | KNR 2-01 0620-01 | Zasypka wykopu fundamentowego (mechanicznie) | m³ | 20–5 000 | 12–25 |
| 20 | KNR 2-01 0620-02 | Zasypka warstwami z zagęszczeniem | m³ | 20–5 000 | 18–38 |
| 21 | KNR 2-01 0630-01 | Odwodnienie wykopu — pompowanie (igłofiltry) | kpl/tydzień | 2–52 | 800–3 500 |
| 22 | KNR 2-01 0631-01 | Igłofiltry — montaż i demontaż | mb | 50–1 000 | 45–120 |
| 23 | KNR 2-01 0640-01 | Drenaż opaskowy ø 100 mm w geowłókninie | mb | 20–2 000 | 85–180 |
| 24 | KNR 2-01 0641-01 | Drenaż podłoża z kruszywa pospółka 16/32 | m³ | 20–2 000 | 85–150 |
| 25 | KNR 4-01 0201-01 | Wymiana gruntu — usunięcie gruntu słabego | m³ | 50–5 000 | 35–80 |
| 26 | KNR 4-01 0202-01 | Wymiana gruntu — dowóz i wbudowanie piasku | m³ | 50–5 000 | 55–120 |
| 27 | KNR 2-01 0701-01 | Roboty ziemne spycharką kat. I-II | m³ | 500–50 000 | 4–10 |
| 28 | KNR 2-01 0702-01 | Plantowanie terenu spycharką | m² | 500–100 000 | 1,50–4,00 |
| 29 | KNR 2-01 0801-01 | Niwelacja mechaniczna z zagęszczeniem | m² | 200–50 000 | 3–8 |
| 30 | KNR 2-01 0900-01 | Roboty ziemne — pobranie i badania geotechniczne | kpl | 1–5 | 2 500–15 000 |

---

### 3.2 Katalog Stawek Maszynowych 2026 (BMSR/SEKOCENBUD)

| Maszyna | Typ / Model ref. | Stawka [PLN/MG] | Uwagi |
|---------|-----------------|-----------------|-------|
| **Koparka gąsienicowa** | 0,8 m³ (Komatsu PC80) | 180–260 | lekkie roboty, rowy |
| **Koparka gąsienicowa** | 1,2 m³ (Cat 320) | 250–320 | standard budownictwa ogólnego |
| **Koparka gąsienicowa** | 2,0 m³ (Cat 336) | 310–420 | nasypy drogowe, ciężkie roboty |
| **Koparka kołowa** | 1,0 m³ (Volvo EC140) | 220–290 | prace miejskie, tereny zabudowane |
| **Koparka podsiębierna** | mała (0,6 m³) | 160–220 | fundamenty, rowy |
| **Spycharka** | 130 KM (Cat D6) | 200–300 | oczyszczanie, niwelacja |
| **Spycharka** | 200 KM (Cat D7) | 290–400 | duże nasypy, trudny teren |
| **Walec wibracyjny** | 12 t | 180–240 | zagęszczenie nasypów |
| **Walec wibracyjny** | 18 t | 220–300 | drogi, autostrada |
| **Zagęszczarka płytowa** | 200 kg | 45–70 | zasypki, chodniki |
| **Ubicak spalinowy** | 60 kg | 35–55 | ciasne miejsca, rowy |
| **Samochód wywrotka** | 10 t (Tatra 815) | 120–180 | wywóz urobku |
| **Samochód wywrotka** | 18 t (Mercedes Actros) | 180–250 | długi transport |
| **Samochód wywrotka** | 30 t (artykułowany) | 280–380 | duże wykopaliska |
| **Koparkoładowarka** | JCB 3CX / Cat 432 | 140–200 | prace mieszane |
| **Grader (równiarka)** | Cat 140 | 260–360 | profilowanie drogi |
| **Skraper** | 14 m³ | 350–500 | nasypy > 5 000 m³ |
| **Igłofiltry (agregat)** | Q=60 m³/h | 400–800/dobę | kpl dobowy |
| **Pompa szlamowa** | Q=50 m³/h | 80–150 | odwodnienie wykopu |
| **Wiertnicy geot.** | do 20 m | 1 200–2 500/otwór | badania gruntu |

**Uwagi do stawek:** Stawki podane bez VAT, na podstawie SEKOCENBUD BMSR Q1-2026 i OWEOB "Orgbud" 2026. Stawki zawierają: amortyzację, paliwo/energię, remonty, ubezpieczenie. Nie zawierają: operatora (doliczyć R = 35–55 PLN/MG), kosztów pośrednich i zysku.

---

### 3.3 Narzuty Kosztorysowe dla Robót Ziemnych 2026

| Składnik | Zakres normatywny | Typowa wartość | Podstawa naliczania |
|----------|------------------|----------------|---------------------|
| Koszty pośrednie (Kp) | 50–65% | 58% | od R+S |
| Zysk (Z) | 5–12% | 7% | od R+S+Kp |
| Ryzyko kontraktu | 2–8% | 4% | od wartości kosztów |
| VAT | 8% (budownictwo mieszkaniowe) lub 23% | 23% | od wartości netto |

---

## CZĘŚĆ 4: CZERWONE FLAGI — 20 RYZYKOWNYCH KLAUZUL SIWZ/SWZ

### Format: Tytuł klauzuli | Opis ryzyka | Jak Terra.OS powinien flagować

---

| # | Tytuł klauzuli | Opis ryzyka | Flaga Terra.OS |
|---|----------------|-------------|----------------|
| **RF-01** | **„Cena ryczałtowa obejmuje wszelkie koszty"** | Wykonawca nie może żądać dodatkowego wynagrodzenia za roboty nieprzewidziane w SIWZ, nawet jeśli są konieczne technologicznie | `FLAG: RYCZAŁT_SZEROKI — sprawdź czy przedmiar zawiera wszystkie pozycje technologicznie wymagane (odwodnienia, obudowy)` |
| **RF-02** | **„Wykonawca zapoznał się z terenem"** | Przeniesienie ryzyka geotechnicznego na wykonawcę. Brak obowiązku GZ (oceny geotechnicznej) po stronie zamawiającego | `FLAG: RYZYKO_GEOTECH — brak badań geotechnicznych w dokumentach przetargu lub brak kategorii geotechnicznej` |
| **RF-03** | **„Termin realizacji nie podlega przedłużeniu z powodu warunków atmosferycznych"** | Roboty ziemne są silnie zależne od pogody. Klauzula eliminuje siłę wyższą (mrozy, powodzie) | `FLAG: WARUNKI_ATMOS — sprawdź czy termin realizacji jest w okresie zimowym (11–3)` |
| **RF-04** | **„Wykonawca odpowiada za obsługę geodezyjną"** | Częste pomijanie kosztów tyczenia, pomiarów kontrolnych i inwentaryzacji powykonawczej | `FLAG: BRAK_GEODEZJI — sprawdź pozycję na obsługę geodezyjną w kosztorysie` |
| **RF-05** | **„Kary umowne za opóźnienie: 0,5%/dzień"** | Kary > 0,3%/dzień są rażące. Łączna kara może przekroczyć wynagrodzenie | `FLAG: KARA_WYSOKA — kara umowna >0,3%/dzień wartości kontraktu, sumaryczna możliwa kara >30% wartości` |
| **RF-06** | **„Gwarancja na roboty ziemne 5 lat"** | Nasypy i wykopy z gwarancją na osiadania i stateczność skarp — ryzyko bardzo trudne do wyceny | `FLAG: GWARANCJA_ZIEMNE — gwarancja na roboty ziemne bez określenia dopuszczalnych tolerancji osiadań` |
| **RF-07** | **„Zamawiający zastrzega prawo zmiany ilości do ±30% bez zmiany ceny jednostkowej"** | Przy spadku ilości o 30% budżet maleje, lecz koszty stałe (mobilizacja, sprzęt) pozostają. Przy wzroście o 30% — niedowycenione pozycje generują stratę | `FLAG: ZMIANA_ILOŚCI_RYCZAŁT — ryzyko asymetryczne przy klauzuli zmiany ilości >20%` |
| **RF-08** | **„Materiały z wykopu stają się własnością Zamawiającego"** | Wykonawca traci urobek jako materiał na nasypy, musi dokupić grunt z zewnątrz | `FLAG: WŁASNOŚĆ_UROBKU — sprawdź czy w kosztorysie uwzględniono zakup materiału nasypowego` |
| **RF-09** | **„Wykonawca jest zobowiązany do opracowania projektu organizacji ruchu na czas budowy"** | Koszt projektu ZRD, uzgodnień, czasowych znaków — często 15 000–50 000 PLN pomijany | `FLAG: BRAK_ZRD — brak pozycji na projekt organizacji ruchu w kosztorysie` |
| **RF-10** | **„Wykonawca ponosi koszty unieszkodliwienia wszystkich odpadów"** | Grunt skażony, azbest, odpady budowlane — koszty utylizacji mogą być wielokrotnie wyższe od robót | `FLAG: ODPADY_RISK — brak pozycji kosztorysowej na utylizację odpadów niebezpiecznych` |
| **RF-11** | **„Wykonawca nie może zlecać prac podwykonawcom bez pisemnej zgody"** | Blokuje podwykonawców sprzętu, co w pracach ziemnych jest standardem | `FLAG: PODWYKONAWCY_BLOK — zakaz lub ograniczenie podwykonawstwa przy robotach wymagających specjalistycznego sprzętu` |
| **RF-12** | **„Płatność po odbiorze końcowym całości"** | Brak płatności częściowych przy robotach trwających >3 miesiące — problem płynności | `FLAG: PLATNOSCI_KONCOWE — brak płatności częściowych (miesięcznych) dla kontraktu >3 miesiące` |
| **RF-13** | **„Wykonawca przejmuje ryzyka wynikające z istnienia niezidentyfikowanej infrastruktury podziemnej"** | Media w terenie (sieci) — kolizje mogą zatrzymać budowę na tygodnie, kosztując 50 000–500 000 PLN | `FLAG: MEDIA_RYZYKO — brak inwentaryzacji mediów lub klauzula przeniesienia ryzyka kolizji na wykonawcę` |
| **RF-14** | **„Cena obejmuje wszystkie opłaty, podatki i opłaty administracyjne"** | Koszty pozwoleń wodnoprawnych, opłat za zajęcie pasa drogowego, wycinki drzew | `FLAG: OPŁATY_ADMIN — brak pozycji na opłaty za zajęcie terenu, pozwolenia specjalne` |
| **RF-15** | **„Wykonawca zobowiązuje się do zachowania terminów pośrednich pod rygorem kary"** | Harmonogram z terminami pośrednimi bez uwzględnienia zależności technologicznych robót ziemnych | `FLAG: TERMINY_POSREDNIE — sprawdź czy harmonogram uwzględnia sezonowość i zależności technologiczne` |
| **RF-16** | **„Zamawiający może żądać wykonania robót dodatkowych po cenach z oferty"** | Wykonawca zobowiązany do robót dodatkowych po cenach ryczałtowych z oferty pierwotnej | `FLAG: ROBOTY_DODATKOWE_CENY — ceny z oferty mogą nie pokrywać kosztów robót dodatkowych innego zakresu` |
| **RF-17** | **„Brak możliwości zmiany wynagrodzenia z powodu wzrostu cen materiałów i sprzętu"** | Przy kontrakcie >12 miesięcy brak klauzuli waloryzacyjnej = ryzyko inflacji cen ropy, stali | `FLAG: BRAK_WALORYZACJI — kontrakt >12 miesięcy bez klauzuli waloryzacyjnej wg GUS lub SEKOCENBUD` |
| **RF-18** | **„Wykonawca odpowiada za archeologię i postępuje zgodnie z wytycznymi WWKZ"** | Odkrycia archeologiczne zatrzymują budowę bezterminowo — koszt opóźnień i nadzoru konserwatorskiego | `FLAG: ARCHEOLOGIA_RYZYKO — brak klauzuli o roszczeniu czasu przy odkryciach archeologicznych` |
| **RF-19** | **„Dokumentacja projektowa zastępuje badania geotechniczne"** | Projekt uproszczony (nie BG) bez aktualnych badań gruntu — ryzyko odmiennych warunków geologicznych | `FLAG: BRAK_BADAŃ_GEOTECH — brak opinii geotechnicznej lub brak badań terenowych w dokumentach przetargu` |
| **RF-20** | **„Wykonawca nie może zgłaszać roszczeń z tytułu wad dokumentacji projektowej"** | Błędy w dokumentacji (zły projekt odwodnienia, nieaktualny przekrój geologiczny) — wykonawca nie może dochodzić wyrównania | `FLAG: BRAK_ROSZCZEN_DOK — klauzula eliminująca roszczenia z tytułu wad dokumentacji przy robotach ziemnych` |

---

## CZĘŚĆ 5: IMPLEMENTACJA W ENGINE L1

### 5.1 Mapowanie Axiomów → Severities Engine

| Severity | Axiomy | Działanie Engine L1 |
|----------|--------|---------------------|
| **CRITICAL** | AX-001, AX-003, AX-004, AX-009, AX-010, AX-011, AX-021, AX-023, AX-024, AX-027, AX-028, AX-029, AX-030, AX-031, AX-043, AX-044, AX-047, AX-048 | `feasible=False`, blokada zatwierdzenia |
| **WARNING** | AX-002, AX-005, AX-006, AX-007, AX-008, AX-012, AX-013, AX-014, AX-015, AX-016, AX-019, AX-020, AX-022, AX-025, AX-026, AX-032, AX-033, AX-034, AX-035, AX-038, AX-041, AX-042, AX-045, AX-049, AX-050 | `feasible=True`, warning w violations |
| **INFO** | AX-018, AX-036, AX-037, AX-039, AX-040, AX-046 | Tylko logi, bez blokady |

---

### 5.2 Szkielet Clingo — Przykładowy Program ASP dla AX-001

```prolog
% ═══════════════════════════════════════════════════════════════
% Terra.OS Engine L1 — Axiom AX-001: Bilans Mas
% CPV 45112000-5, norma PN-B-06050:1999 §4.2
% ═══════════════════════════════════════════════════════════════

% Fakty wejściowe (generowane z przedmiaru)
% wykop_vol(TenderId, ObjM3).
% nasyp_vol(TenderId, ObjM3).
% wywoz_vol(TenderId, ObjM3).

% Reguła bilans mas
tolerancja_bilans(0.05).  % 5%

mass_imbalance(T, Diff) :-
    wykop_vol(T, V1),
    nasyp_vol(T, V2),
    wywoz_vol(T, V3),
    tolerancja_bilans(Tol),
    Diff = V1 - V2 - V3,
    |Diff| > Tol * V1.

violation(T, "AX-001", "CRITICAL",
    "Bilans mas niezachowany: wykop - nasyp - wywóz = Diff m³") :-
    mass_imbalance(T, Diff).

% Weryfikacja Z3 (SMT):
% assert wykop_vol >= 0
% assert nasyp_vol >= 0
% assert wywoz_vol >= 0
% assert |wykop_vol - nasyp_vol - wywoz_vol| <= 0.05 * wykop_vol
```

---

### 5.3 Struktura danych — Przedmiar Item dla Robót Ziemnych

```json
{
  "przedmiar_item": {
    "id": "pi_001",
    "lp": 1,
    "knr_code": "KNR 2-01 0120-01",
    "cpv_code": "45112000-5",
    "axiom_tags": ["AX-001", "AX-003", "AX-021"],
    "description": "Wykop koparką w gruncie kat. I-II — odkład",
    "unit": "m3",
    "quantity": 1500.0,
    "unit_price_pln": 14.50,
    "line_total_pln": 21750.00,
    "metadata": {
      "grunt_kategoria": "II",
      "wskaznik_spulchnienia": 1.10,
      "glebokos_m": 1.8,
      "sprzet": "koparka_gąsienicowa_1.2m3"
    }
  }
}
```

---

### 5.4 Priorytety Walidacji L1

```
Faza 1 — CRITICAL SAFETY (blokada bezwarunkowa):
  AX-027 (nachylenie skarp), AX-030 (wykop >4m), AX-031 (rów wąski)
  
Faza 2 — CRITICAL MASS_BALANCE (blokada kosztorysowa):
  AX-001 (bilans mas), AX-003 (nasyp > wykop), AX-004 (wymiana gruntu)

Faza 3 — CRITICAL SEQUENCE (blokada logiczna):
  AX-021 (kolejność nasyp/wykop), AX-022 (humus), AX-023 (obudowa)

Faza 4 — CRITICAL DRAINAGE (blokada techniczna):
  AX-009 (brak odwodnienia), AX-010 (kolejność odwodnienia)

Faza 5 — WARNINGS (raport do PM):
  Wszystkie WARNING z AX-002 do AX-050

Faza 6 — INFO (dashboard metrics):
  AX-018, AX-036, AX-037, AX-039, AX-040, AX-046
```

---

## PODSUMOWANIE

| Element | Zawartość |
|---------|-----------|
| Axiomy CRITICAL | 18 reguł (blokują kosztorys) |
| Axiomy WARNING | 26 reguł (ostrzeżenia) |
| Axiomy INFO | 6 reguł (metryki) |
| Kody CPV | 25 kodów szczegółowych |
| Pozycje kosztorysowe | 30 top pozycji KNR 2-01 |
| Stawki maszynowe | 20 pozycji sprzętu |
| Czerwone flagi SIWZ | 20 klauzul ryzyka |
| Clingo pseudokod | 50 wzorców ASP |

**Podstawy normatywne:** PN-B-06050:1999, PN-EN 1997-1:2008 (EC7), PN-S-02205:1998, GDDKiA WT-4:2010, KNR 2-01, SEKOCENBUD Q1-2026, BHP Dz.U. 2003 nr 47, Ustawa Prawo Budowlane, Ustawa o odpadach 2012.

---

*Dokument wygenerowany przez Civil Engineer Agent 🏗️ — Agency Agents dla Terra.OS*  
*Projekt: Terra.OS AI Engine dla polskich firm budowlanych*  
*Następny batch: Roboty betonowe (CPV 45262300), Instalacje sanitarne (CPV 45330000)*
