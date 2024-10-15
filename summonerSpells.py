# Utils/getSummonerSpellNameByID.py

def get_summoner_spell_name(spell_id):
    summoner_spells = {
        1: ("<:cleanse:1284542770471636992>", "Cleanse"),
        3: ("<:exhaust:1284542781716435024>", "Exhaust"),
        4: ("<:flash:1284542789689933975>", "Flash"),
        6: ("<:ghost:1284542796140904580>", "Ghost"),
        7: ("emo<:heal:1284542803057180682>jiID", "Heal"),
        11: ("<:smite:1284542809138790461>", "Smite"),
        12: ("<:teleport:1284542815237570610>", "Teleport"),
        13: ("<:clarity:1284542820614672436>", "Clarity"),
        14: ("<:ignite:1284542826214064168>", "Ignite"),
        21: ("<:barrier:1284542831171735654>", "Barrier"),
        30: ("<:totheking:1284542836028477500>", "To the King!"),
        31: ("<:porotoss:1284542841938251826>", "Poro Toss"),
        32: ("<:mark:1284542847013617755>", "Mark/Dash"),
        39: ("<:mark:1284542847013617755>", "URF Mark"),
        54: ("<:spellbookplaceholder:1284542853178982421>", "Ult. Spellbook"),
        55: ("<:spellbooksmite:1284542858510073957>", "Auto-Smite"),
        2201: ("<:Flee:1284542864969306242>", "Flee"),
        2202: ("<:arenaFlash:1284542871298642061>", "Flash")
    }
    return summoner_spells.get(spell_id, ("<:spellbookplaceholder:1284542853178982421>", "Unknown Spell"))
