"""
Narrative Generation for Overtake System.

Generates descriptive text for Confronting Dice overtake outcomes
suitable for the Anchor fanfic.
"""

from typing import Dict, List


def generate_confrontation_narrative(
    result, attacker_name: str, defender_name: str, situation_name: str = ""
) -> str:
    """
    Generate narrative text for a confrontation.

    Args:
        result: ConfrontationResult from OvertakeConfrontation
        attacker_name: Name of the attacking driver
        defender_name: Name of the defending driver
        situation_name: Optional description of the situation

    Returns:
        Formatted narrative string
    """
    lines = []

    # Header
    lines.append(f"[CONFRONTATION: {attacker_name} vs {defender_name}]")
    if situation_name:
        lines.append(f"_{situation_name}_")
    lines.append("")

    # Attacker breakdown
    lines.append(f"**ATTACKER ({attacker_name})**: 1d10 = {result.attacker_roll}")
    for mod_name, mod_value in sorted(result.attacker_modifiers.items()):
        lines.append(f"  + {mod_name}: {mod_value:+.1f}")
    lines.append(f"  = **TOTAL: {result.attacker_total:.1f}**")
    lines.append("")

    # Defender breakdown
    lines.append(f"**DEFENDER ({defender_name})**: 1d10 = {result.defender_roll}")
    for mod_name, mod_value in sorted(result.defender_modifiers.items()):
        lines.append(f"  + {mod_name}: {mod_value:+.1f}")
    lines.append(f"  = **TOTAL: {result.defender_total:.1f}**")
    lines.append("")

    # Separator
    lines.append("━" * 32)

    # Result
    if result.winner == "attacker":
        margin_desc = _get_margin_description(result.margin)
        lines.append(f"**WINNER: {attacker_name.upper()}**")
        lines.append(f"Margin: {result.margin:.1f} ({margin_desc})")
        lines.append("━" * 32)
        lines.append("")
        lines.append(
            _generate_attacker_win_narrative(attacker_name, defender_name, result)
        )

    elif result.winner == "tie":
        lines.append("**RESULT: TIE**")
        lines.append("━" * 32)
        lines.append("")
        lines.append(f"**{defender_name}** holds the position!")
        lines.append("_Tie goes to the defender._")

    else:  # defender wins
        if result.push_available:
            lines.append(f"**PUSH OPPORTUNITY** (margin: {result.margin:.1f})")
            lines.append("━" * 32)
            lines.append("")
            lines.append(_generate_push_narrative(attacker_name, defender_name, result))
        else:
            margin_desc = _get_margin_description(result.margin)
            lines.append(f"**WINNER: {defender_name.upper()}**")
            lines.append(f"Margin: {result.margin:.1f} ({margin_desc})")
            lines.append("━" * 32)
            lines.append("")
            lines.append(
                _generate_defender_win_narrative(attacker_name, defender_name, result)
            )

    return "\n".join(lines)


def _get_margin_description(margin: float) -> str:
    """Get description of the margin size"""
    if margin <= 1:
        return "nose-to-nose"
    elif margin <= 3:
        return "close battle"
    elif margin <= 5:
        return "clear advantage"
    else:
        return "dominant"


def _generate_attacker_win_narrative(attacker: str, defender: str, result) -> str:
    """Generate narrative for attacker win"""
    narratives = [
        f"**{attacker}** executes a bold move, sweeping inside to claim the position!",
        f"**{attacker}** finds the gap and lunges past **{defender}** into the corner!",
        f"**{attacker}** shows superior pace, easing past **{defender}** with authority.",
        f"**{attacker}** makes it stick, completing a clinical overtake on **{defender}**.",
        f"**{attacker}** times it perfectly, diving inside to demote **{defender}**.",
    ]
    return narratives[int(result.margin) % len(narratives)]


def _generate_defender_win_narrative(attacker: str, defender: str, result) -> str:
    """Generate narrative for defender win"""
    narratives = [
        f"**{defender}** closes the door decisively, forcing **{attacker}** to back out.",
        f"**{defender}** defends brilliantly, keeping **{attacker}** at bay through the corner.",
        f"**{defender}** holds the inside line, nullifying **{attacker}**'s attack.",
        f"**{attacker}** throws everything at it, but **{defender}** remains unfazed.",
        f"**{defender}** makes no mistake, defending the position with racecraft.",
    ]
    return narratives[int(result.margin) % len(narratives)]


def _generate_push_narrative(attacker: str, defender: str, result) -> str:
    """Generate narrative for push opportunity"""
    return (
        f"**{attacker}** isn't done yet! The gap is closing—can they find a way through?\n"
        f"_A push could change everything..._"
    )


def generate_situation_description(situation_type: str, track_name: str) -> str:
    """Generate a brief description of the overtake situation"""

    situation_descriptions = {
        "in_drs_zone": f"into the DRS zone, {track_name}",
        "end_of_drs_zone": f"at the {track_name} corner exit",
        "elsewhere": f"around the {track_name} circuit",
    }

    return situation_descriptions.get(situation_type, f"at {track_name}")


def generate_overtake_headline(result, position: int, track: str) -> str:
    """
    Generate a short headline for race reports.

    Args:
        result: ConfrontationResult
        position: Position number
        track: Track name

    Returns:
        Headline string
    """
    if result.winner == "attacker":
        return f"P{position}: Exciting overtake at {track}"
    elif result.winner == "tie":
        return f"P{position}: Defensive masterclass at {track}"
    else:
        return f"P{position}: Close battle at {track}"
