from textual.theme import Theme

# The heat scale, empty to full: each step's background, then its text
HEAT = (
    ("#1A1826", "#8E89A6"),
    ("#163B33", "#BDEBDD"),
    ("#1F6B58", "#DDF8EF"),
    ("#33A487", "#04140F"),
    ("#54E1B8", "#06231C"),
)

AURORA = Theme(
    name="aurora",
    dark=True,
    foreground="#E9E7F2",
    background="#08070D",
    surface="#100F18",
    panel="#0C0B13",
    primary="#A99BFF",
    secondary="#71B7FF",
    accent="#54E1B8",
    success="#54E1B8",
    warning="#FFC46B",
    error="#FF7E93",
    variables={
        "border": "#26233A",
        "border-blurred": "#1D1A2A",
        "border-strong": "#34304A",
        "text-muted": "#8E89A6",
        "footer-background": "#0C0B13",
        "warning-surface": "#1A1508",
        "warning-border": "#4A3A16",
        **{f"heat-{step}": bg for step, (bg, _) in enumerate(HEAT)},
        **{f"heat-{step}-text": fg for step, (_, fg) in enumerate(HEAT)},
    },
)
"""i18n-ai's one theme, dark: v2's ink, violet for the app, mint for what is done, amber for
fallbacks, coral for errors, sky for what runs."""
