/** @odoo-module **/

import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('test_survey_roaming_mandatory_questions_with_triggers', {
    url: '/survey/start/af192191-7966-49c8-8ae5-d86bd7b6773d',
    steps: () => [{
        content: 'Click on Start',
        trigger: 'button.btn:contains("Start")',
        run: "click",
    },
    {
        content: 'Skip question Q1',
        trigger: 'button.btn:contains("Continue")',
        run: "click",
    },
    {
        trigger: 'div.js_question-wrapper:contains("Q3")',
    },
    {
        content: 'Click on Submit',
        trigger: 'button.btn:contains("Submit")',
        run: "click",
    },
    {
        content: 'Check if question is Q1',
        trigger: 'div.js_question-wrapper:contains("Q1")',
    },
    {
        content: 'Answer Q1 with the answer triggering Q2',
        trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 2")',
        run: "click",
    },
    {
        content: 'Check if the visible question is the triggered question Q2',
        trigger: 'div.js_question-wrapper:contains("Q2")',
    },
    {
        content: 'Answer Q2',
        trigger: 'div.js_question-wrapper:contains("Q2") label:contains("Answer 3")',
        run: "click",
    },
    {
        trigger: 'div.js_question-wrapper:contains("Q3")',
    },
    {
        content: 'Answer Q3',
        trigger: 'div.js_question-wrapper:contains("Q3") label:contains("Answer 1")',
        run: "click",
    },
    {
        content: 'Click on Submit',
        trigger: 'button.btn:contains("Submit")',
        run: "click",
    },
    {
        content: 'Check if the survey is done',
        trigger: 'div.o_survey_finished h1:contains("Thank you!")',
    }],
});
