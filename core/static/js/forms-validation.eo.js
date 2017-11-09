/**
 * Esperanto translation for HTML5 form constraint validation messages.
 * Meir <interDist@users.noreply.github.com>
 */
(function ($) {
    if (typeof $.fn.localConstraint === "undefined") {
        $.fn.extend({ localConstraint: {} });
    }
    $.fn.localConstraint['eo'] = {
        valueMissing__file: "Bonvole elektu dosieron.",
        valueMissing__number: "Bonvole provizu numeron.",
        valueMissing__date: "Bonvole provizu daton.",
        valueMissing__email: "Bonvole provizu retpoŝtan adreson.",
        valueMissing__radio: "Bonvole elektu unu el tiuj ĉi opcioj.",
        valueMissing__checkbox: "Bonvole marku ĉi tie por daŭrigi.",
        valueMissing__select: "Bonvole elektu unu opcion el la listo.",
        valueMissing__select__multiple: "Bonvole elektu almenaŭ unu opcion el la listo.",
        valueMissing: "Bonvole ne lasu tiun ĉi kampon malplena.",
        valueMismatch__password: "La du pasvortaj kampoj ne kongruas.",
        typeMismatch__email: "Bonvole provizu ĝusta-forman retpoŝtan adreson.",
        typeMismatch__email__multiple: "Bonvole provizu liston de retpoŝtadresoj en ĝusta formo.",
        typeMismatch__url: "Bonvole provizu ĝusta-forman retadreson (URL).",
        patternMismatch: "La formato de provizita de vi %(datum)s estas malĝusta.",
        patternMismatch__default: "dateno",
        tooLong: "Bonvole uzu ne pli ol %(limit)s signoj (vi uzis jam %(len)s).",
        tooShort: "Bonvole uzu almenaŭ %(limit)s signojn (vi uzis nur %(len)s).",
        minmax: "La numero devas esti inter %(min)s kaj %(max)s.",
        minmax__date: "Bonvole indiku daton inter %(min)s kaj %(max)s.",
        minmax__time: "Bonvole indiku tempon inter %(min)s kaj %(max)s.",
        min: "La numero devas esti ne pli malalta ol %(min)s.",
        min__date: "Bonvole indiku daton ne pli fruan ol %(min)s.",
        min__time: "Bonvole indiku tempon ne pli fruan ol %(min)s.",
        max: "La numero devas esti ne pli alta ol %(max)s.",
        max__date: "Bonvole indiku daton ne pli malfruan ol %(max)s.",
        max__time: "Bonvole indiku tempon ne pli malfruan ol %(max)s.",
        max__file: "Bonvole provizu malpli grandan dosieron.",
        stepMismatch__number: "Maltaŭga valoro; la plej proksimaj estas %(low)s kaj %(high)s.",
        stepMismatch__number__one: "Maltaŭga valoro; la plej proksima taŭga estas %(low)s.",
        stepMismatch: "Bonvole provizu taŭgan valoron.",
        badInput__number: "Bonvole provizu nur numeron, sen aldonaj signoj.",
        badInput__email: "La retpoŝtadreso enhavas malpermesitajn signojn aŭ malhavas necesajn signojn.",
        badInput: "Bonvole provizu ĝusta-forman valoron.",
    };
} (jQuery));
