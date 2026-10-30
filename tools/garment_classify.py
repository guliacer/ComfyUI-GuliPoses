"""服装库归类规则：按「穿的是什么」分，而不是按季节分。

源库原本按 8 个季节目录（01_spring … 08_sexy）分系列，用户找图时对不上——
想找一条百褶裙，得在春夏秋冬四个 tab 里各翻一遍。这里改成按品类归类。

归类依据只有两样东西：编号前缀（场景线索）和英文关键词里的「主件」。
- 主件决定一级类型（系列 tab）：连衣裙 / 半身裙 / 裤装 / 上装 / 内衣·家居 / 泳装
- 同一主件下的修饰词决定二级类型（分类下拉）：迷你 / 中长 / 长款 / 百褶 / 牛仔 …
- 外套、开衫、配饰（bag/socks/stockings/heels…）是叠加层，不参与一级判定，
  否则「针织开衫 + 迷你裙」会被判成上装。

两条必须靠前缀的例外：
- LNG-* 是居家内衣套装，「camisole + shorts」里的 shorts 是睡裤，不能当外穿短裤。
- SWM-* 里只有一部分真的带 swimsuit 关键词，其余是普通夏装，按关键词走。

被 build_garment_db.py 与 retag_garment.py 共用；改规则后重跑 retag 即可，
不需要重新复制图片。
"""

# 一级类型的展示顺序：数量多的在前，内衣/泳装靠后，认不出来的垫底
SERIES_ORDER = ["dress", "skirt", "pants", "top", "innerwear", "swimwear", "other"]

SERIES_NAME = {
    "dress": "连衣裙",
    "skirt": "半身裙",
    "pants": "裤装",
    "top": "上装",
    "innerwear": "内衣·家居",
    "swimwear": "泳装",
    "other": "其它",
}

# 编号前缀 → 原始场景，写进 season 字段供画廊搜索（搜「春」能翻到春季那批）。
# 实测前缀与目录名不同名：08_sexy 的图叫 SXY-xxxx、06_party 的图叫 PTY-xxxx，
# 老的 SEX/PAR 一起留着，以后源库改名也不必回来动这里。
SEASON_BY_PREFIX = {
    "SPR": "春",
    "SUM": "夏",
    "AUT": "秋",
    "WIN": "冬",
    "LNG": "内衣",
    "PTY": "派对",
    "PAR": "派对",
    "SWM": "泳装",
    "SXY": "性感",
    "SEX": "性感",
}

# 关键词 → 二级分类。按顺序匹配，先命中先算。
# 同一件衣服可能同时带 mini 和 pleated，百褶更能说明款式，所以百褶排在迷你前面。
DRESS_STEPS = [("maxi", "连衣裙·长款"), ("midi", "连衣裙·中长"), ("mini", "连衣裙·迷你")]
SKIRT_STEPS = [("pleated", "半身裙·百褶"), ("midi", "半身裙·中长"), ("mini", "半身裙·迷你")]
TOP_STEPS = [
    ({"knit", "cardigan", "sweater"}, "上装·针织"),
    ({"blouse", "shirt", "turtleneck"}, "上装·衬衫"),
    ({"camisole", "vest", "tank"}, "上装·吊带"),
    ({"jacket", "coat"}, "上装·外套"),
    ({"hoodie"}, "上装·卫衣"),
]
# 有这些词但没任何外穿下装 → 内衣（外穿下装指的是一级判定里的 dress/skirt/pants 那批）
INNER_TOPS = {"bra", "briefs", "corset", "robe", "lingerie"}
# 这些词出现说明有外穿下装，内衣判定要让位
OUTER_BOTTOMS = {"dress", "skirt", "pants", "jeans", "shorts"}

# 人工复核过的修正表：源关键词把「主件词」漏了，只写了材质和配饰
# （`satin gloves heels`、`grey pleated loafers bag`），规则只能判成「其它」。
# 这 14 条逐张看图确认后钉死在这里，不放宽规则——`pleated` 多数场合指裤褶而非百褶裙，
# 放宽会把普通长裤吸进半身裙。规则能判对的一律不进本表。
# 键是编号（不含前缀之外的任何东西），值只写 (series_key, cat)，中文名从 SERIES_NAME 取。
OVERRIDES = {
    # 派对晚礼服：及地缎面挂脖开衩长裙，关键词只有 satin / gloves / heels
    "PTY-0003": ("dress", "连衣裙·长款"),
    "PTY-0006": ("dress", "连衣裙·长款"),
    "PTY-0022": ("dress", "连衣裙·长款"),
    "PTY-0027": ("dress", "连衣裙·长款"),
    "PTY-0039": ("dress", "连衣裙·长款"),
    "PTY-0052": ("dress", "连衣裙·长款"),
    # 阔腿 / 直筒长裤：关键词缺 pants，或 pleated 指的是裤褶
    "SPR-0246": ("pants", "裤装·阔腿"),
    "AUT-0173": ("pants", "裤装·阔腿"),
    "AUT-0251": ("pants", "裤装·阔腿"),
    "SUM-0192": ("pants", "裤装·长裤"),
    "AUT-0177": ("pants", "裤装·长裤"),
    "AUT-0182": ("pants", "裤装·长裤"),
    # 连体裤：上身连下装，一件到底，既不是连衣裙也不是普通长裤
    "SUM-0217": ("pants", "裤装·连体"),
    "SUM-0230": ("pants", "裤装·连体"),
}


def _hit(word_set: set, step) -> bool:
    """step 既可以是单词，也可以是词集合。"""
    if isinstance(step, str):
        return step in word_set
    return bool(word_set & step)


def season_of(code: str) -> str:
    """编号前缀对应的原始场景名；认不出来就留空，不编造。"""
    return SEASON_BY_PREFIX.get(code.split("-")[0].upper(), "")


def classify(code: str, keywords: str) -> tuple[str, str, str]:
    """(series_key, series_name, cat) —— 一级类型 / 一级中文名 / 二级分类。"""
    words = {w.lower() for w in (keywords or "").split()}
    prefix = code.split("-")[0].upper()

    # 0) 人工复核过的条目优先，它比任何规则都准
    override = OVERRIDES.get(code.strip().upper())
    if override:
        key, cat = override
        return key, SERIES_NAME[key], cat

    # 1) 泳装：唯一有确定关键词的类型，先摘出来
    if "swimsuit" in words:
        return "swimwear", SERIES_NAME["swimwear"], "泳装"

    # 2) 居家内衣：前缀是 LNG 就一定是，别被里面的 shorts 带跑
    if prefix == "LNG":
        if "corset" in words:
            return "innerwear", SERIES_NAME["innerwear"], "内衣·连体"
        if "robe" in words:
            return "innerwear", SERIES_NAME["innerwear"], "内衣·家居服"
        return "innerwear", SERIES_NAME["innerwear"], "内衣·套装"

    # 3) 关键词里只有内衣、没有外穿下装 → 也是内衣
    if words & INNER_TOPS and not words & OUTER_BOTTOMS:
        if "corset" in words:
            return "innerwear", SERIES_NAME["innerwear"], "内衣·连体"
        if "robe" in words:
            return "innerwear", SERIES_NAME["innerwear"], "内衣·家居服"
        return "innerwear", SERIES_NAME["innerwear"], "内衣·套装"

    # 4) 连衣裙：dress 是完整一件，优先级高于任何下装词
    if "dress" in words:
        for step, cat in DRESS_STEPS:
            if _hit(words, step):
                return "dress", SERIES_NAME["dress"], cat
        return "dress", SERIES_NAME["dress"], "连衣裙·常规"

    # 5) 半身裙
    if "skirt" in words:
        for step, cat in SKIRT_STEPS:
            if _hit(words, step):
                return "skirt", SERIES_NAME["skirt"], cat
        return "skirt", SERIES_NAME["skirt"], "半身裙·常规"

    # 6) 裤装：牛仔长裤 / 长裤 / 短裤
    if "jeans" in words:
        return "pants", SERIES_NAME["pants"], "裤装·牛仔"
    if "pants" in words:
        return "pants", SERIES_NAME["pants"], "裤装·长裤"
    if "shorts" in words:
        return "pants", SERIES_NAME["pants"], "裤装·短裤"

    # 7) 只剩上衣：靠上装词细分
    for step, cat in TOP_STEPS:
        if _hit(words, step):
            return "top", SERIES_NAME["top"], cat

    # 8) 关键词里一个服装词都没有（只剩颜色 / bag / heels / gloves 这类配饰）：
    #    与其塞进「上装」冒充品类，不如单列「其它」，找上装的人不会翻到一堆派对礼服。
    return "other", SERIES_NAME["other"], "其它"


def series_counts(poses) -> list[dict]:
    """按 SERIES_ORDER 生成 index.json 的 series 数组；没有货的类型不出现。"""
    from collections import Counter

    counter = Counter(p["series"] for p in poses)
    out = []
    for key in SERIES_ORDER:
        count = counter.get(key, 0)
        if not count:
            continue
        name = SERIES_NAME[key]
        out.append(
            {
                "key": key,
                "name": name,
                "nameJp": name,
                "short": name,
                "count": count,
            }
        )
    return out


def cat_counts(poses) -> list[tuple[str, int]]:
    """二级分类 → 数量，按一级顺序再按数量降序，便于确认有没有孤零零的小类。"""
    from collections import Counter

    order = {key: i for i, key in enumerate(SERIES_ORDER)}
    counter = Counter((p["series"], p["cat"]) for p in poses)
    return sorted(counter.items(), key=lambda kv: (order.get(kv[0][0], 99), -kv[1]))
