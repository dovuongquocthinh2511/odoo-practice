# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class DemoClass(models.Model):
    _name = "demo_course.class"
    _description = "Class"

    name = fields.Char('Class Name', required=True)
    # khai báo field many2one:
    course_id = fields.Many2one('demo_course.course', string='Course', ondelete='cascade') # ondelete: 'set null', 'restrict', 'cascade'
    student_ids = fields.Many2many('demo_course.student', 
                                    string="Students", 
                                    relation='class_student_rel',
                                    column1='col_class_id',
                                    column2='col_student_id')
    register_id = fields.Many2one('demo_course.register', compute='compute_register', inverse='register_inverse')
    register_ids = fields.One2many('demo_course.register', 'class_id')

    @api.depends('register_ids')
    def compute_register(self):
        for record in self:
            if len(record.register_ids) > 0:
                record.register_id = record.register_ids[0]
            else:
                record.register_id = False 
                

    def register_inverse(self):
        for record in self:
            if len(record.register_ids) > 0:
                # delete previous reference
                register = self.env['demo_course.register'].browse(record.register_ids[0].id)
                register.class_id = False
            # set new reference
            record.register_id.class_id = record.id
            
class DemoCourse(models.Model):
    _name = "demo_course.course"
    _description = "Course"

    name = fields.Char('Course Name', required=True)    
    # khai báo field one2many:
    class_ids = fields.One2many('demo_course.class', inverse_name='course_id', string='Classes')
    
class DemoStudent(models.Model):
    _name = "demo_course.student"
    _description = "Course"

    name = fields.Char('Student Name', required=True) 
    class_ids = fields.Many2many('demo_course.class', 
                                    string="Classes", 
                                    relation='class_student_rel',
                                    column1='col_student_id',
                                    column2='col_class_id')
    # khai báo field age
    age = fields.Integer()  
    name_age_combine = fields.Char()
    name_age_compute = fields.Char(compute="compute_name_age_combine_field")
    age_copy = fields.Integer(compute="copy_age", inverse="reverse_age")
    
    # validate field "name" và "age" theo các điều kiện:
    @api.constrains('name', 'age')
    def validate_student_info(self):
        for record in self:
            if record.age < 10:
                raise ValidationError("Age is not allowed to be less than 10.")
            if len(record.name) > 15:
                raise ValidationError("Too long name for student (%d>15)." % len(record.name))
     
    # tính toán cập nhật:
    @api.onchange('name', 'age')
    def update_name_age_combine_field(self):
        for record in self:
            if record.name:
                record.name_age_combine = record.name + " (%d)  " % record.age
    
    @api.depends('name', 'age')
    def compute_name_age_combine_field(self):
        for record in self:
            if record.name: 
                record.name_age_compute = record.name + " (%d)" % record.age
            else:
                record.name_age_compute = False

    @api.depends('age')
    def copy_age(self):
        for record in self:
            if record.age != record.age_copy:
                record.age_copy = record.age

    def reverse_age(self):
        for record in self: 
            record.age = record.age_copy

class DemoRegister(models.Model):
    _name = "demo_course.register"
    _description = "Register"

    name = fields.Char('Register Name', required=True)
    # Hiện thực field one2one ở model còn lại:
    class_id = fields.Many2one('demo_course.class', string='Class')
       