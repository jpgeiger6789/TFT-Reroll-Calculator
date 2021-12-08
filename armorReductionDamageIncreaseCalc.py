def armorRedBonusDmg(baseArmor, percentReduction):
    
    ArmorReduction = 100/(100 + baseArmor)

    reducedArmorReduction = 100 / (100 + baseArmor * percentReduction)

    baseDamage = 1 * ArmorReduction

    increasedDamage = 1 * reducedArmorReduction

    damageIncrease = (increasedDamage - baseDamage) / baseDamage

    return damageIncrease
