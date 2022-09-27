from common.base_prod import TECH_COST_MULTIPLIER
from common.misc import MIN_RECOLONIZING_HAPPINESS, MIN_RECOLONIZING_SIZE
from common.priorities import AFTER_ALL_TARGET_MAX_METERS_PRIORITY
from species.common.population import GROWTH_RATE_FACTOR

Tech(
    name="SHP_GAL_EXPLO",
    description="SHP_GAL_EXPLO_DESC",
    short_description="POLICY_UNLOCK_SHORT_DESC",
    category="SHIP_PARTS_CATEGORY",
    researchcost=1 * TECH_COST_MULTIPLIER,
    researchturns=1,
    tags=["PEDIA_SHIP_PARTS_CATEGORY", "THEORY"],
    unlock=Item(type=UnlockPolicy, name="PLC_EXPLORATION"),
    effectsgroups=[
        EffectsGroup(
            scope=Planet(size=Tiny) & OwnedBy(empire=Source.Owner),
            accountinglabel="TINY_PLANET_LABEL",
            effects=SetMaxSupply(value=Value + 2),
        ),
        EffectsGroup(
            scope=Planet(size=Small) & OwnedBy(empire=Source.Owner),
            accountinglabel="SMALL_PLANET_LABEL",
            effects=SetMaxSupply(value=Value + 1),
        ),
        EffectsGroup(
            scope=Planet(size=Large) & OwnedBy(empire=Source.Owner),
            accountinglabel="LARGE_PLANET_LABEL",
            effects=SetMaxSupply(value=Value - 1),
        ),
        EffectsGroup(
            scope=Planet(size=Huge) & OwnedBy(empire=Source.Owner),
            accountinglabel="HUGE_PLANET_LABEL",
            effects=SetMaxSupply(value=Value - 2),
        ),
        EffectsGroup(
            scope=Planet(type=GasGiantType) & OwnedBy(empire=Source.Owner),
            accountinglabel="GAS_GIANT_LABEL",
            effects=SetMaxSupply(value=Value - 1),
        ),
        EffectsGroup(  # outpost supply increases 1 per turn up to max
            scope=Planet() & OwnedBy(empire=Source.Owner) & ~HasSpecies,
            priority=AFTER_ALL_TARGET_MAX_METERS_PRIORITY,
            effects=SetSupply(value=MinOf(float, Value(Target.MaxSupply), Value + 1)),
        ),
        # generate sitrep for any planet that is about to reach minimum population and stability
        # to be a source for colony ships and buildings
        EffectsGroup(
            scope=Planet()
            & OwnedBy(empire=Source.Owner)
            & CanColonize
            & (LocalCandidate.Population < LocalCandidate.TargetPopulation)
            & (
                LocalCandidate.Population
                + LocalCandidate.Population
                * GROWTH_RATE_FACTOR
                * (1 + (1 - LocalCandidate.Population) / LocalCandidate.TargetPopulation)
                >= MIN_RECOLONIZING_SIZE
            )
            & (LocalCandidate.TargetHappiness >= MIN_RECOLONIZING_HAPPINESS)
            & (
                LocalCandidate.Happiness
                + 1
                + NamedRealLookup(name="PLC_CAPITAL_MARKETS_INFLUENCE_RATE")
                * StatisticIf(
                    float, condition=Source & EmpireHasAdoptedPolicy(empire=Source.Owner, name="PLC_CAPITAL_MARKETS")
                )
                >= MIN_RECOLONIZING_HAPPINESS
            )
            & (
                ((0.1 <= LocalCandidate.Happiness) & (LocalCandidate.Happiness <= (MIN_RECOLONIZING_HAPPINESS - 0.001)))
                | ((0.1 <= LocalCandidate.Population) & (LocalCandidate.Population <= (MIN_RECOLONIZING_SIZE - 0.001)))
            ),
            effects=[
                GenerateSitRepMessage(
                    message="SITREP_POP_THRESHOLD",
                    label="SITREP_POP_THRESHOLD_LABEL",
                    icon="icons/sitrep/colony_growth.png",
                    parameters={"planet": Target.ID},
                    empire=Source.Owner,
                )
            ],
        ),
        EffectsGroup(
            scope=Source,
            activation=Turn(low=0, high=0),
            effects=[
                GenerateSitRepMessage(
                    message="SITREP_WELCOME",
                    label="SITREP_WELCOME_LABEL",  # explicitly provided so that the custom SitRep intro message can share the same SitRepPanel filter
                    icon="icons/sitrep/fo_logo.png",
                    empire=Source.Owner,
                )
            ],
        ),
    ],
    graphic="icons/tech/galactic_exploration.png",
)
