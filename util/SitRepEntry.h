#ifndef _SitRepEntry_h_
#define _SitRepEntry_h_

//! @file
//!     Declares the SitRepEntry calls and related factory functions.

#include "VarText.h"

#include <string>
#include <vector>

#include "Export.h"

//! Represents a situation report entry for a significant game event.
class FO_COMMON_API SitRepEntry : public VarText {
public:
    SitRepEntry();

    SitRepEntry(const char* template_string, int turn, const char* icon,
                const char* label, bool stringtable_lookup);

    SitRepEntry(std::string&& template_string, int turn, std::string&& icon,
                std::string&& label, bool stringtable_lookup);

    [[nodiscard]] int                GetDataIDNumber(const std::string& tag) const;
    [[nodiscard]] const std::string& GetDataString(const std::string& tag) const;
    [[nodiscard]] int                GetTurn() const         { return m_turn; }
    [[nodiscard]] const std::string& GetIcon() const         { return m_icon; }
    [[nodiscard]] const std::string& GetLabelString() const  { return m_label; }
    [[nodiscard]] std::string        Dump() const;

private:
    int         m_turn;
    std::string m_icon;
    std::string m_label;

    friend class boost::serialization::access;
    template <typename Archive>
    void serialize(Archive& ar, const unsigned int version);
};

//! @name SitRepEntry factories
//!
//! Factory functions to create SitRepEntry(s) for specific situation report
//! events.
//!
//! @{
[[nodiscard]] SitRepEntry CreateTechResearchedSitRep(const std::string& tech_name);
[[nodiscard]] SitRepEntry CreateShipBuiltSitRep(int ship_id, int system_id, int shipdesign_id);
[[nodiscard]] SitRepEntry CreateShipBlockBuiltSitRep(int system_id, int shipdesign_id, int number);
[[nodiscard]] SitRepEntry CreateBuildingBuiltSitRep(int building_id, int planet_id);

[[nodiscard]] SitRepEntry CreateTechUnlockedSitRep(const std::string& tech_name);
[[nodiscard]] SitRepEntry CreatePolicyUnlockedSitRep(const std::string& policy_name);
[[nodiscard]] SitRepEntry CreateBuildingTypeUnlockedSitRep(const std::string& building_type_name);
[[nodiscard]] SitRepEntry CreateShipHullUnlockedSitRep(const std::string& ship_hull_name);
[[nodiscard]] SitRepEntry CreateShipPartUnlockedSitRep(const std::string& ship_part_name);

[[nodiscard]] FO_COMMON_API SitRepEntry CreateCombatSitRep(int system_id, int log_id, int empire_id);
[[nodiscard]] FO_COMMON_API SitRepEntry CreateGroundCombatSitRep(int planet_id, int empire_id);
[[nodiscard]] FO_COMMON_API SitRepEntry CreatePlanetCapturedSitRep(int planet_id, int empire_id);
[[nodiscard]] FO_COMMON_API SitRepEntry CreatePlanetRebelledSitRep(int planet_id, int empire_id);
[[nodiscard]] FO_COMMON_API SitRepEntry CreateCombatDamagedObjectSitRep(int object_id, int combat_system_id, int empire_id);
[[nodiscard]] FO_COMMON_API SitRepEntry CreateCombatDestroyedObjectSitRep(int object_id, int combat_system_id, int empire_id);
[[nodiscard]] SitRepEntry               CreatePlanetDepopulatedSitRep(int planet_id);
[[nodiscard]] FO_COMMON_API SitRepEntry CreatePlanetColonizedSitRep(int planet_id, const std::string& species);
[[nodiscard]] FO_COMMON_API SitRepEntry CreatePlanetOutpostedSitRep(int planet_id);

[[nodiscard]] FO_COMMON_API SitRepEntry CreatePlanetGiftedSitRep(int planet_id, int empire_id);
[[nodiscard]] FO_COMMON_API SitRepEntry CreateFleetGiftedSitRep(int fleet_id, int empire_id);

[[nodiscard]] FO_COMMON_API SitRepEntry CreateFleetArrivedAtDestinationSitRep(int system_id, int fleet_id, int recipient_empire_id);
[[nodiscard]] SitRepEntry               CreateEmpireEliminatedSitRep(int empire_id);
[[nodiscard]] SitRepEntry               CreateVictorySitRep(const std::string& reason_string, int empire_id);
[[nodiscard]] FO_COMMON_API SitRepEntry CreateSitRep(const std::string& template_string, int turn,
                                                     const std::string& icon,
                                                     std::vector<std::pair<std::string, std::string>> parameters,
                                                     const std::string& label = "", bool stringtable_lookup = true);
//! @}

template <typename Archive>
void SitRepEntry::serialize(Archive& ar, const unsigned int version)
{
    ar  & BOOST_SERIALIZATION_BASE_OBJECT_NVP(VarText)
        & BOOST_SERIALIZATION_NVP(m_turn)
        & BOOST_SERIALIZATION_NVP(m_icon)
        & BOOST_SERIALIZATION_NVP(m_label);
}


#endif
