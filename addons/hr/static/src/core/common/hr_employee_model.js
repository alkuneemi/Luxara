import { Record, fields } from "@mail/core/common/record";
import { user } from "@web/core/user";

export class HrEmployee extends Record {
    static _name = "hr.employee";
    static id = "id";
    static getRelevantEmployee(employees) {
        const activeEmployees = (employees ?? []).filter((e) => e.active);
        const activeCompanyId = user.activeCompany?.id;
        const sortedEmployees = activeEmployees.sort(
            (e1, e2) =>
                (e2.company_id?.id === activeCompanyId) - (e1.company_id?.id === activeCompanyId) ||
                (e1.user_id?.id ?? Infinity) - (e2.user_id?.id ?? Infinity) ||
                e2.id - e1.id
        );
        return sortedEmployees[0];
    }

    /** @type {Boolean} */
    active;
    /** @type {number} */
    id;
    /** @type {number} */
    company_id = fields.One("res.company");
    department_id = fields.One("hr.department");
    /** @type {string} */
    job_title;
    work_contact_id = fields.One("res.partner");
    user_id = fields.One("res.users");
    /** @type {string} */
    work_email;
    work_location_id = fields.One("hr.work.location");
    /** @type {string} */
    work_phone;
}

HrEmployee.register();
