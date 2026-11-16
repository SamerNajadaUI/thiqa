"""
مواصفات استعلامات Wikidata لبنك «جمع نقاط».
كل مواصفة بترجّع كيانات إلها: تسمية عربية (مش لاتيني)، صورة، عدد sitelinks (مقياس شهرة)، ووجود مقالة بالعربي.
بنشغّلها بالـCI (الجلسة ما بتوصل Wikidata): engine/wd_fetch.py → engine/wd/<key>.json
"""

ARAB = "wd:Q810 wd:Q851 wd:Q79 wd:Q796 wd:Q858 wd:Q822 wd:Q219060 wd:Q817 wd:Q878 wd:Q846 wd:Q398 wd:Q842 wd:Q805 wd:Q1028 wd:Q262 wd:Q948 wd:Q1016 wd:Q1049 wd:Q1025 wd:Q1045 wd:Q977 wd:Q970"

# خصائص إضافية: اسم → (خاصية، نوع) ؛ label = تسمية عربية للقيمة، year = سنة، num = رقم
EXTRA = {
    "country": ("P17", "label"), "city": ("P131", "label"), "continent": ("P30", "label"),
    "citizen": ("P27", "label"), "gender": ("P21", "id"), "born": ("P569", "year"), "died": ("P570", "year"),
    "inception": ("P571", "year"), "height": ("P2048", "num"), "elev": ("P2044", "num"), "pop": ("P1082", "num"),
    "area": ("P2046", "num"), "creator": ("P170", "label"), "maker": ("P176", "label"), "origin": ("P495", "label"),
    "inventor": ("P61", "label"), "discovered": ("P575", "year"), "published": ("P577", "year"), "director": ("P57", "label"),
    "developer": ("P178", "label"), "sport": ("P641", "label"), "occupation": ("P106", "label"), "located": ("P276", "label"),
    "length": ("P2043", "num"), "architect": ("P84", "label"), "collection": ("P195", "label"), "team": ("P54", "label"),
    "position": ("P413", "label"), "nat_sport": ("P1532", "label"), "capital": ("P36", "label"), "currency": ("P38", "label"),
    "language": ("P37", "label"), "founder": ("P112", "label"), "hq": ("P159", "label"), "parent": ("P749", "label"),
    "industry": ("P452", "label"), "cast": ("P161", "label"), "genre": ("P136", "label"), "series": ("P179", "label"),
    "platform": ("P400", "label"), "publisher": ("P123", "label"), "symbol": ("P246", "str"), "atomic": ("P1086", "num"),
    "head_state": ("P35", "label"), "anthem": ("P85", "label"), "dialcode": ("P474", "str"), "tld": ("P78", "label"),
    "water": ("P206", "label"), "range": ("P4552", "label"), "basin": ("P4614", "label"), "parent_taxon": ("P171", "label"),
    "awards": ("P166", "count"), "children": ("P1971", "num"), "followers": ("P8687", "num"), "employer": ("P108", "label"),
    "field": ("P101", "label"), "notable": ("P800", "label"), "movement": ("P135", "label"), "brand": ("P1716", "label"),
    "owner": ("P127", "label"), "operator": ("P137", "label"), "capacity": ("P1083", "num"), "tenant": ("P466", "label"),
    "winner": ("P1346", "label"), "season_of": ("P3450", "label"), "start": ("P580", "year"), "end": ("P582", "year"),
    "point_time": ("P585", "year"), "location": ("P276", "label"), "participants": ("P710", "label"), "mother_tongue": ("P103", "label"),
    "religion": ("P140", "label"), "spouse": ("P26", "label"), "father": ("P22", "label"), "dynasty": ("P53", "label"),
    "member_of": ("P463", "label"), "flag": ("P41", "file"), "logo": ("P154", "file"), "map": ("P242", "file"), "locator": ("P1943", "file"),
}


def S(key, where, img="P18", min_sl=30, extra=(), limit=2000, need_img=True, arwiki=False, note=""):
    return dict(key=key, where=where, img=img, min_sl=min_sl, extra=list(extra), limit=limit, need_img=need_img, arwiki=arwiki, note=note)


def cls(*qids, sub=False):
    path = "wdt:P31/wdt:P279*" if sub else "wdt:P31"
    return "VALUES ?cls { %s } ?item %s ?cls ." % (" ".join("wd:" + q for q in qids), path)


def occ(*qids):
    return "?item wdt:P31 wd:Q5 . VALUES ?occ { %s } ?item wdt:P106 ?occ ." % " ".join("wd:" + q for q in qids)


def named(*en, prop="wdt:P171*"):
    """كيانات تحت تصنيفات معروفة باسمها الإنجليزي (عشان ما نغلط بأرقام QID)."""
    vals = " ".join('"%s"@en' % x for x in en)
    return "VALUES ?nm { %s } ?anc rdfs:label ?nm . ?item %s ?anc . ?item wdt:P105 ?rank . VALUES ?rank { wd:Q7432 wd:Q34740 wd:Q35409 wd:Q37517 }" % (vals, prop)


def under(*en, depth2=True):
    """أشياء (مش كائنات حية) نوعها أو أصلها واحد من هالأصناف، لمستويين."""
    vals = " ".join('"%s"@en' % x for x in en)
    base = "VALUES ?nm { %s } ?root rdfs:label ?nm . " % vals
    if depth2:
        return base + "{ ?item wdt:P31|wdt:P279 ?root . } UNION { ?item wdt:P31|wdt:P279 ?mid . ?mid wdt:P279 ?root . }"
    return base + "?item wdt:P31|wdt:P279 ?root ."


def taxon(q):
    return "?item wdt:P171* wd:%s . ?item wdt:P105 ?rank . VALUES ?rank { wd:Q7432 wd:Q34740 wd:Q35409 wd:Q37517 }" % q


SPECS = [
    # ---------- أماكن ----------
    S("landmarks", cls("Q570116", "Q4989906", "Q179700", "Q12518", "Q2977", "Q44539", "Q174782", "Q22698", "Q1107656", "Q24398318"), min_sl=45,
      extra=("country", "city", "inception", "height", "architect")),
    S("whs", "?item wdt:P1435 wd:Q9259 .", min_sl=30, extra=("country", "city", "inception")),
    S("castles", cls("Q23413", "Q16560", "Q751876", "Q1785071", "Q57821", sub=False), min_sl=22, extra=("country", "city", "inception")),
    S("mosques", cls("Q32815", sub=True), min_sl=12, extra=("country", "city", "inception", "architect")),
    S("churches", cls("Q2977", "Q16970", "Q56242215", "Q2031836", sub=False), min_sl=40, extra=("country", "city", "inception")),
    S("bridges", cls("Q12280", sub=True), min_sl=20, extra=("country", "city", "inception", "length", "water")),
    S("museums", cls("Q33506", sub=True), min_sl=30, extra=("country", "city", "inception")),
    S("ancient", cls("Q839954", "Q15661340", "Q109607", "Q1060829", "Q44539", "Q12516", sub=False), min_sl=30, extra=("country", "city", "inception")),
    S("waterfalls", cls("Q34038", sub=True), min_sl=15, extra=("country", "height", "water")),
    S("mountains", cls("Q8502", "Q8072", "Q46831", sub=False), min_sl=30, extra=("country", "elev", "continent", "range")),
    S("islands", cls("Q23442", "Q33837", "Q1402592", sub=False), min_sl=40, extra=("country", "area", "continent", "water")),
    S("lakes_rivers", cls("Q23397", "Q4022", "Q1322134", sub=False), min_sl=60, extra=("country", "length", "area", "continent")),
    S("cities", cls("Q515", "Q1637706", "Q5119", "Q200250", "Q1549591", sub=False), min_sl=80, extra=("country", "pop", "continent", "inception")),
    S("stadiums", cls("Q483110", sub=True), min_sl=20, extra=("country", "city", "capacity", "tenant", "inception")),
    S("countries", cls("Q6256", "Q3624078", sub=False), min_sl=100, img="P41",
      extra=("capital", "currency", "continent", "language", "pop", "area", "inception", "dialcode", "map", "locator")),
    # ---------- ناس ----------
    S("actors", occ("Q33999", "Q10800557", "Q10798782"), min_sl=70, extra=("citizen", "gender", "born", "died")),
    S("actors_arab", occ("Q33999", "Q10800557", "Q10798782") + " ?item wdt:P27 ?ac . VALUES ?ac { %s }" % ARAB, min_sl=8, arwiki=True,
      extra=("citizen", "gender", "born", "died")),
    S("singers", occ("Q177220", "Q488205", "Q2252262", "Q855091"), min_sl=60, extra=("citizen", "gender", "born", "died", "genre")),
    S("singers_arab", occ("Q177220", "Q488205", "Q639669", "Q36834") + " ?item wdt:P27 ?ac . VALUES ?ac { %s }" % ARAB, min_sl=8, arwiki=True,
      extra=("citizen", "gender", "born", "died")),
    S("scientists", occ("Q901", "Q169470", "Q593644", "Q170790", "Q205375", "Q11063", "Q864503", "Q2374149", "Q350979"), min_sl=60,
      extra=("citizen", "gender", "born", "died", "field", "notable")),
    S("historic_arab", "?item wdt:P31 wd:Q5 . ?item wdt:P570 ?dd . FILTER(YEAR(?dd) < 1990) ?item wdt:P27 ?ac . VALUES ?ac { %s }" % ARAB,
      min_sl=30, arwiki=True, extra=("citizen", "gender", "born", "died", "occupation")),
    S("islamic_people", "?item wdt:P31 wd:Q5 . ?item wdt:P140 wd:Q432 . ?item wdt:P570 ?dd . FILTER(YEAR(?dd) < 1500)", min_sl=25, need_img=False,
      arwiki=True, extra=("born", "died", "occupation", "father", "spouse")),
    S("athletes", occ("Q3665646", "Q10833314", "Q11338576", "Q10841764", "Q11513337", "Q10843402", "Q11607585", "Q12299841", "Q13381863"),
      min_sl=60, extra=("citizen", "gender", "born", "sport")),
    S("wrestlers", occ("Q13474373"), min_sl=18, extra=("citizen", "gender", "born")),
    S("coaches", occ("Q628099"), min_sl=40, extra=("citizen", "gender", "born")),
    S("arabplayers", occ("Q937857") + " ?item wdt:P1532 ?ac . VALUES ?ac { %s }" % ARAB, min_sl=12, arwiki=True,
      extra=("nat_sport", "gender", "born", "position")),
    S("astronauts", occ("Q11631"), min_sl=40, extra=("citizen", "gender", "born")),
    # ---------- طبيعة ----------
    S("mammals", taxon("Q7377"), min_sl=60, extra=("parent_taxon",)),
    S("birds", taxon("Q5113"), min_sl=60, extra=("parent_taxon",)),
    S("cetaceans", taxon("Q160"), min_sl=35, extra=("parent_taxon",)),
    S("dog_breeds", cls("Q39367"), min_sl=18, extra=("origin",)),
    S("cat_breeds", cls("Q43577"), min_sl=15, extra=("origin",)),
    S("horse_breeds", cls("Q1160573"), min_sl=20, extra=("origin",)),
    S("fruits", "?item (wdt:P31|wdt:P279)/wdt:P279* wd:Q3314483 .", min_sl=40),
    S("vegetables", "?item (wdt:P31|wdt:P279)/wdt:P279* wd:Q11004 .", min_sl=40),
    S("planets_space", cls("Q634", "Q1055", "Q2537", "Q8928", "Q318", "Q42372", "Q3559", "Q523", "Q148578", "Q26529", "Q25956", "Q40218", sub=False),
      min_sl=45, extra=("discovered", "inventor")),
    # ---------- أكل وأشياء ----------
    S("dishes", "?item (wdt:P31|wdt:P279)/wdt:P279* wd:Q746549 .", min_sl=30, extra=("origin", "country")),
    S("drinks", "?item (wdt:P31|wdt:P279)/wdt:P279* wd:Q40050 .", min_sl=35, extra=("origin", "country")),
    S("instruments", "?item (wdt:P31|wdt:P279)/wdt:P279* wd:Q34379 .", min_sl=30, extra=("origin",)),
    S("car_models", cls("Q3231690", sub=True), min_sl=35, extra=("maker", "inception", "origin")),
    S("inventions", "?item wdt:P61 ?inv . FILTER NOT EXISTS { ?item wdt:P31 ?bad . VALUES ?bad { wd:Q5 wd:Q16521 wd:Q11344 wd:Q523 wd:Q3863 wd:Q2537 wd:Q65943 wd:Q207961 wd:Q1153690 } }",
      min_sl=45, extra=("inventor", "discovered", "inception")),
    S("currencies", cls("Q8142", sub=False), min_sl=40, extra=("country",)),
    S("paintings", cls("Q3305213"), min_sl=25, extra=("creator", "collection", "inception")),
    # ---------- شعارات ----------
    S("airlines", cls("Q46970"), img="P154", min_sl=25, extra=("country",)),
    S("car_brands", cls("Q786820", "Q44294", sub=False), img="P154", min_sl=30, extra=("country", "inception", "parent")),
    S("orgs", cls("Q484652", "Q1335818", "Q15925165", "Q163740", "Q245065", sub=False), img="P154", min_sl=50, extra=("inception",)),
    S("companies", cls("Q4830453", "Q891723", "Q6881511", "Q783794", sub=False), img="P154", min_sl=60,
      extra=("country", "founder", "inception", "industry", "hq")),
    S("websites_apps", cls("Q35127", "Q620615", "Q3220391", "Q1668024", "Q7397", sub=False), img="P154", min_sl=40,
      extra=("country", "founder", "inception", "developer")),
    S("clubs", cls("Q476028"), img="P154", min_sl=40, extra=("country", "city", "inception")),
    # ---------- كتابي: أفلام وألعاب وتكنولوجيا وتاريخ ----------
    S("films", cls("Q11424", "Q202866", "Q24862", sub=False), min_sl=70, need_img=False, extra=("director", "published", "cast", "origin", "genre", "series")),
    S("tv_series", cls("Q5398426", "Q581714", "Q1259759", sub=False), min_sl=50, need_img=False, extra=("published", "origin", "cast", "genre")),
    S("arab_films", cls("Q11424", "Q5398426", "Q581714", sub=False) + " ?item wdt:P495 ?ac . VALUES ?ac { %s }" % ARAB, min_sl=6, need_img=False,
      arwiki=True, extra=("director", "published", "cast", "origin")),
    S("videogames", cls("Q7889"), min_sl=45, need_img=False, extra=("developer", "publisher", "published", "series", "genre", "platform")),
    S("tech_companies", cls("Q4830453", "Q891723", "Q6881511", "Q783794", sub=False) +
      " ?item wdt:P452 ?ind . VALUES ?ind { wd:Q880371 wd:Q11661 wd:Q11650 wd:Q638608 wd:Q2401742 wd:Q1137109 wd:Q418 wd:Q627335 wd:Q1062279 }",
      min_sl=40, need_img=False, extra=("country", "founder", "inception", "hq")),
    S("prog_langs", cls("Q9143", sub=False), min_sl=40, need_img=False, extra=("developer", "inception", "inventor")),
    S("events", cls("Q178561", "Q198", "Q131569", "Q3839081", "Q1190554", "Q124757", "Q7283", "Q8076", sub=False), min_sl=80, need_img=False,
      extra=("point_time", "start", "end", "location", "country")),
    S("elements", cls("Q11344"), min_sl=50, need_img=False, extra=("symbol", "atomic", "discovered", "inventor")),
    S("league_seasons", "?item wdt:P3450 ?lg . VALUES ?lg { wd:Q9448 wd:Q324867 wd:Q82595 wd:Q15804 wd:Q13394 wd:Q18756 wd:Q35572 wd:Q18278 wd:Q19570 wd:Q201181 wd:Q1023283 wd:Q749096 wd:Q605734 wd:Q1123166 wd:Q1062491 wd:Q1069549 } ?item wdt:P1346 ?w .",
      min_sl=1, need_img=False, limit=3000, extra=("winner", "season_of", "start", "end")),
    S("jordan_places", "?item wdt:P17 wd:Q810 . VALUES ?cls { wd:Q515 wd:Q3957 wd:Q532 wd:Q133442 wd:Q570116 wd:Q839954 wd:Q23413 wd:Q15661340 wd:Q46169 wd:Q8502 wd:Q4022 } ?item wdt:P31 ?cls .",
      min_sl=8, need_img=False, arwiki=True, extra=("city", "pop", "inception", "elev")),
]

# ---------- دفعة 2: بدل اللي وقف بالتايم آوت ----------
SPECS += [
    S("towers", cls("Q11303", "Q12518", "Q1021645", "Q18142"), min_sl=25, extra=("country", "city", "inception", "height")),
    S("historic_pol", occ("Q116", "Q11900058", "Q47064", "Q189290") + " ?item wdt:P570 ?dd . FILTER(YEAR(?dd) < 1960)", min_sl=90,
      extra=("citizen", "gender", "born", "died", "occupation")),
    S("historic_art", occ("Q1028181", "Q36834", "Q36180", "Q49757", "Q4964182", "Q11063", "Q170790", "Q169470") + " ?item wdt:P570 ?dd . FILTER(YEAR(?dd) < 1960)",
      min_sl=110, extra=("citizen", "gender", "born", "died", "occupation")),
    S("celebs_tv", occ("Q947873", "Q4610556", "Q17125263", "Q15077007", "Q18814623"), min_sl=40, extra=("citizen", "gender", "born", "occupation")),
    S("celebs_biz", occ("Q131524", "Q43845"), min_sl=70, extra=("citizen", "gender", "born", "occupation")),
    S("reptiles", named("Squamata", "Testudines", "Crocodilia", "Rhynchocephalia"), min_sl=40, extra=("parent_taxon",)),
    S("amphibians", named("Anura", "Caudata", "Gymnophiona"), min_sl=30, extra=("parent_taxon",)),
    S("dinos", named("Ornithischia", "Sauropodomorpha", "Tyrannosauridae", "Dromaeosauridae", "Spinosauridae", "Allosauridae", "Ceratosauria",
                     "Abelisauridae", "Carcharodontosauridae", "Ornithomimosauria", "Therizinosauria", "Oviraptorosauria", "Pterosauria",
                     "Plesiosauria", "Ichthyosauria", "Mosasauridae"), min_sl=18, extra=("parent_taxon",)),
    S("sea_more", named("Cephalopoda", "Decapoda", "Echinodermata", "Scyphozoa", "Anthozoa", "Pinnipedia", "Sirenia", "Cheloniidae",
                        "Selachimorpha", "Batoidea", "Syngnathidae", "Tetraodontidae", "Scombridae", "Salmonidae", "Pomacentridae", "Muraenidae",
                        "Lophiiformes", "Xiphiidae", "Istiophoridae", "Hippocampus"), min_sl=35, extra=("parent_taxon",)),
    S("insects2", named("Apidae", "Formicidae", "Coccinellidae", "Odonata", "Mantodea", "Caelifera", "Ensifera", "Blattodea", "Culicidae",
                        "Muscidae", "Vespidae", "Papilionidae", "Nymphalidae", "Pieridae", "Phasmatodea", "Scarabaeidae", "Lampyridae", "Cicadidae",
                        "Siphonaptera", "Phthiraptera", "Lucanidae", "Cerambycidae", "Sphingidae", "Saturniidae", "Bombycidae", "Termitoidae",
                        "Scorpiones", "Araneae", "Ixodida", "Chilopoda", "Diplopoda"), min_sl=35, extra=("parent_taxon",)),
    S("flowers", named("Rosaceae", "Orchidaceae", "Liliaceae", "Iridaceae", "Ranunculaceae", "Amaryllidaceae", "Papaveraceae", "Oleaceae",
                       "Malvaceae", "Cactaceae", "Nymphaeaceae", "Lamiaceae", "Violaceae", "Ericaceae", "Magnoliaceae", "Asparagaceae",
                       "Caryophyllaceae", "Paeoniaceae", "Hydrangeaceae", "Geraniaceae", "Primulaceae", "Nelumbonaceae", "Araceae",
                       "Bromeliaceae", "Asteraceae", "Solanaceae", "Brassicaceae", "Apiaceae", "Fabaceae", "Cucurbitaceae"),
      min_sl=55, extra=("parent_taxon",)),
    S("trees", named("Pinaceae", "Cupressaceae", "Fagaceae", "Arecaceae", "Moraceae", "Salicaceae", "Betulaceae", "Sapindaceae", "Juglandaceae",
                     "Ulmaceae", "Platanaceae", "Myrtaceae", "Lauraceae", "Anacardiaceae", "Rutaceae", "Ebenaceae", "Bignoniaceae", "Ginkgoaceae",
                     "Taxaceae", "Araucariaceae"), min_sl=45, extra=("parent_taxon",)),
    S("spices", under("spice", "herb", "condiment"), min_sl=25),
    S("gems", under("gemstone", "mineral", "precious metal"), min_sl=35),
    S("desserts", under("dessert", "cake", "confectionery", "pastry", "cookie", "candy", "ice cream"), min_sl=20, extra=("origin", "country")),
    S("tools", under("tool", "hand tool", "power tool", "kitchen utensil", "measuring instrument"), min_sl=30),
    S("sportsgear", under("sports equipment", "ball", "protective equipment", "exercise equipment"), min_sl=20),
    S("aircraft", cls("Q15056995", "Q15056993", "Q1420", "Q34486", "Q40218"), min_sl=30, extra=("maker", "inception")),
    S("costumes", under("traditional costume", "folk costume", "garment", "headgear", "dress"), min_sl=15, extra=("origin", "country")),
    S("dances", under("dance", "folk dance", "dance style"), min_sl=15, extra=("origin", "country")),
    S("tournaments", under("association football competition", "sports competition", "football tournament", "multi-sport event", "tennis tournament"),
      img="P154", min_sl=35),
    S("olympics", "VALUES ?nm { \"Summer Olympic Games\"@en \"Winter Olympic Games\"@en } ?c rdfs:label ?nm . ?item wdt:P31 ?c .", min_sl=20,
      need_img=False, extra=("country", "city", "point_time", "start")),
    S("jordan_gov", "?c rdfs:label \"governorate of Jordan\"@en . ?item wdt:P31 ?c .", min_sl=1, need_img=False, extra=("capital", "pop", "area")),
    S("vehicles", under("motor vehicle", "watercraft", "rail vehicle", "bicycle", "aircraft"), min_sl=40),
    S("fruits2", under("fruit", "berry", "citrus", "nut", "edible fruit"), min_sl=25),
    S("vegetables2", under("vegetable", "leaf vegetable", "root vegetable", "legume", "herb"), min_sl=25),
]
