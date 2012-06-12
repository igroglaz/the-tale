if (!window.pgf) {
    pgf = {};
}

if (!pgf.game) {
    pgf.game = {};
}

if (!pgf.game.widgets) {
    pgf.game.widgets = {};
}

if (!pgf.game.events) {
    pgf.game.events = {};
}

pgf.game.events.ANGEL_DATA_REFRESHED = 'pgf-angel-data-refreshed';
pgf.game.events.ANGEL_DATA_REFRESH_NEEDED = 'pgf-angel-data-refresh-needed';

pgf.game.AngelUpdater = function(params) {

    var instance = this;

    this.data = {};

    this.Refresh = function() {
        
        jQuery.ajax({
            dataType: 'json',
            type: 'get',
            url: params.url,
            data: {}, 
            success: function(answer, request, status) {

                instance.data = answer.data;

                jQuery(document).trigger(pgf.game.events.ANGEL_DATA_REFRESHED, instance.data);
            },
            error: function() {
            },
            complete: function() {
            }
        });
    };

    jQuery(document).bind(pgf.game.events.ANGEL_DATA_REFRESH_NEEDED, function(e){
        instance.Refresh();
    });
};

pgf.game.widgets.Angel = function(selector, params) {

    var content = jQuery(selector);
    var data = undefined;

    function RenderAngel() {
        if (!data) return;

        jQuery('.pgf-energy', content).text(data.energy.value);
        jQuery('.pgf-max-energy', content).text(data.energy.max);

        pgf.base.UpdateStatsBar(jQuery('.pgf-energy-bar', content), data.energy.max, data.energy.value);
    };

    function Refresh(angel_data) {
        data = angel_data.angel;
    };

    function Render() {
        RenderAngel();
    };

    jQuery(document).bind(pgf.game.events.ANGEL_DATA_REFRESHED, function(e, angel_data){
        Refresh(angel_data);
        Render();
    });
};

pgf.game.widgets.Abilities = function(selector, widgets, params) {
    var instance = this;

    var abilities = pgf.game.data.abilities;

    var widget = jQuery(selector);
    var deckContainer = jQuery('.pgf-abilities-list', widget);
    var activateAbilityWidget = jQuery('#activate-ability-block');
    var activateAbilityFormWidget = jQuery('.pgf-activate-form', activateAbilityWidget);
    var tooltipTemplate = jQuery(params.tooltipTemplate);

    jQuery('.pgf-cancel', activateAbilityWidget).click(function(e){
        e.preventDefault();
        //TODO: replace with some kind of api not related to widgets
        widgets.switcher.ShowMapWidget();
    });

    var angelId = undefined;
    var deck = {};
    var turn = {};

    function LockAbility(abilityType) {
        jQuery('.ability-'+abilityType, widget).toggleClass('cooldown', true);
    }

    function ActivateAbility(ability) {

        var abilityInfo = abilities[ability.type];

        if (ability.available_at > turn.number) return;
        if (abilityInfo.limited && ability.limit == 0) return;
        
        //TODO: replace with some kind of api not related to widgets
        var currentHero = widgets.heroes.CurrentHero();

        var heroId = -1;
        if (currentHero) {
            heroId = currentHero.id;
        }

        if (abilityInfo.use_form) { 

            //TODO: replace with some kind of api not related to widgets
            widgets.switcher.ShowActivateAbilityWidget();

            function OnSuccessActivation(form, data) {
                ability.available_at = data.data.available_at;
                ability.limit = data.data.limit;

                if (ability.available_at) LockAbility(ability.type);
                if (abilityInfo.limited && ability.limit == 0) LockAbility(ability.type);

                //TODO: replace with some kind of api not related to widgets
                widgets.switcher.ShowMapWidget();

                jQuery(document).trigger(pgf.game.events.ANGEL_DATA_REFRESH_NEEDED);
                jQuery(document).trigger(pgf.game.events.DATA_REFRESH_NEEDED);
            }

            jQuery.ajax({
                type: 'get',
                url: pgf.urls['game:abilities:form'](ability.type),
                success: function(data, request, status) {
                    activateAbilityFormWidget.html(data);

                    formSelector = jQuery('form', activateAbilityFormWidget);

                    jQuery('#id_angel_id', formSelector).val(angelId);
                    jQuery('#id_hero_id', formSelector).val(heroId);

                    var activationForm = new pgf.forms.Form(formSelector,
                                                            {action: pgf.urls['game:abilities:activate'](ability.type),
                                                             OnSuccess: OnSuccessActivation});
                },
                error: function(request, status, error) {
                },
                complete: function(request, status) {
                }
            });
        }
        else {
            var ajax_data = {};
            if (heroId !== undefined) {
                ajax_data.hero_id = heroId;
                ajax_data.angel_id = angelId;
            }
            pgf.forms.Post({action: pgf.urls['game:abilities:activate'](ability.type),
                            data: ajax_data,
                            OnSuccess: function(data) {
                                ability.available_at = data.data.available_at;
                                ability.limit = data.data.limit;

                                if (ability.available_at) LockAbility(ability.type);
                                if (abilityInfo.limited && ability.limit == 0) LockAbility(ability.type);

                                jQuery(document).trigger(pgf.game.events.ANGEL_DATA_REFRESH_NEEDED);
                                jQuery(document).trigger(pgf.game.events.DATA_REFRESH_NEEDED);
                            }
                           });
        }
        
    }

    function RenderAbilityTootltip(tooltip, ability) {
        var abilityInfo = abilities[ability.type]
        jQuery('.pgf-name', tooltip).text(abilityInfo.name);
        jQuery('.pgf-description', tooltip).text(abilityInfo.description);
        jQuery('.pgf-artistic', tooltip).text(abilityInfo.artistic);

        if (abilityInfo.limited) {
            jQuery('.pgf-limited', tooltip).toggleClass('pgf-hidden', false);
            jQuery('.pgf-limited .pgf-limit-number', tooltip).text(ability.limit);
            jQuery('.pgf-limited .pgf-can-use', tooltip).toggleClass('pgf-hidden', ability.limit==0);
            jQuery('.pgf-limited .pgf-limit-exceeded', tooltip).toggleClass('pgf-hidden', ability.limit!=0);
        }

        return tooltip;
    };

    function RenderAbility(index, ability, element) {
        var abilityInfo = abilities[ability.type]
        jQuery('.pgf-name', element).text(abilityInfo.name);
        element.addClass( 'ability-'+abilityInfo.type.toLowerCase() );

        if (ability.available_at > turn.number) LockAbility(ability.type);
        if (abilityInfo.limited && ability.limit == 0) LockAbility(ability.type);

        element.click(function(e){
            // e.preventDefault();
            ActivateAbility(ability);
        });

        var tooltipContainer = jQuery('.pgf-tooltip-container', element);
        var tooltip = tooltipTemplate.clone().removeClass('pgf-hidden');
        tooltipContainer.html(RenderAbilityTootltip(tooltip, ability));
    }

    function RenderDeck() {
        pgf.base.RenderTemplateList(deckContainer, deck, RenderAbility, {});
    };

    function Refresh(event_data) {
        deck = event_data.angel.abilities;
        angelId = event_data.angel.id;
        turn = event_data.turn;
    };

    function Render() {
        RenderDeck();
    };

    jQuery(document).bind(pgf.game.events.ANGEL_DATA_REFRESHED, function(e, event_data){
        Refresh(event_data);
        Render();
    });
};


