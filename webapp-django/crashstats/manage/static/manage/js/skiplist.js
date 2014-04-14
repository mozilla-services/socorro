/*global alert:true location:true */
(function ($, document) {
    'use strict';

    function start_loading() {
        $('.pleasewait').show();
    }

    function stop_loading() {
        $('.pleasewait').hide();
    }

    function render_data(callback) {
        var $form = $('form.filter');
        var category = $.trim($('input[name="category"]', $form).val());
        var rule = $.trim($('input[name="rule"]', $form).val());
        var data = {category: category, rule: rule};
        start_loading();
        $.getJSON(location.href + 'data/', data, function(response) {
            var $tbody = $('.results tbody');
            $('tr', $tbody).remove();
            $.each(response.hits, function(i, each) {
                $('<tr>')
                  .append($('<td>').text(each.category))
                  .append($('<td>').text(each.rule))
                  .append($('<td>')
                     .append($('<input type="button" value="Delete">')
                            .click(function() {
                                delete_skiplist(each.category, each.rule);
                            })))
                  .appendTo($tbody);
            });
            stop_loading();
        });
    }

    function delete_skiplist(category, rule) {
        start_loading();
        var csrfmiddlewaretoken = $('form.filter input[name="csrfmiddlewaretoken"]').val();
        var data = {category: category, rule: rule, csrfmiddlewaretoken: csrfmiddlewaretoken};
        start_loading();
        $.post(location.href + 'delete/', data, function(response) {
            render_data();
        });
    }

    function submit_form($form) {
        var $category = $('input[name="category"]', $form);
        var category = $.trim($category.val());
        var $rule = $('input[name="rule"]', $form);
        var rule = $.trim($rule.val());
        var csrfmiddlewaretoken = $('input[name="csrfmiddlewaretoken"]', $form).val();
        if (category && rule) {
            var data = {category: category, rule: rule, csrfmiddlewaretoken: csrfmiddlewaretoken};
            start_loading();
            $.post($form.attr('action'), data, function(response) {
                $category.val('');
                $rule.val('');
                render_data();
            });
        } else {
            alert("Must have both category and rule");
        }
        return false;
    }

    function filter_form($form) {
        render_data();
        return false;
    }

    $(document).ready(function() {

        // hijack form submissions
        $('form.add').submit(function() {
            return submit_form($(this));
        });

        $('form.filter').submit(function() {
            $('form.filter input.reset').show();
            return filter_form($(this));
        });

        $('form.filter input.reset').click(function() {
            $(this).hide();
            $('form.filter input[name="category"]').val('');
            $('form.filter input[name="rule"]').val('');
            render_data();
            return false;
        });

        if ($('form.filter input[name="category"]').val() || $('form.filter input[name="rule"]').val()) {
            $('form.filter input.reset').show();
        } else {
            $('form.filter input.reset').hide();
        }

        render_data();

    });

}($, document));
