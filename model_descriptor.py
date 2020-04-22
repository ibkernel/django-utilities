from typing import NamedTuple

from django.db import connections
from django.db.models import Model


class Field(NamedTuple):
    name: str
    db_type: str
    description: str
    primary_key: bool
    foreign_key: bool
    choices: list

    @property
    def markdown_repr(self):
        return (
            f'| {self.name} '
            f'| {"PK, " if self.primary_key else ""}{"FK, " if self.foreign_key else ""}{self.db_type} '
            f'| {self.description} |\n'
        )

    @property
    def plantuml_entity_repr(self):
        return (
            f'\t{self.name}: {"PK, " if self.primary_key else ""}{"FK, " if self.foreign_key else ""}{self.db_type}\n'
        )


class ModelDescriptor:

    def __init__(self, model: Model):
        self._meta = model._meta
        self._model_description = model.__doc__.replace(' ', '').replace('\n', '')
        self._fields = []
        self._db_indexes = []
        self._unique_constraints = []

        self._load()

    def _load(self):
        meta = self._meta
        connection = connections[meta.app_label]
        fields = meta.fields
        for django_field in fields:
            self._fields.append(Field(
                name=django_field.name,
                db_type=django_field.db_type(connection).upper(),
                description=(
                    django_field.verbose_name if django_field.verbose_name != django_field.name.replace('_', ' ') else
                    ''
                ),
                primary_key=django_field.primary_key,
                foreign_key=(
                    True if hasattr(django_field, 'remote_field') and django_field.remote_field is not None else False
                ),
                choices=django_field.choices
            ))

            if not django_field.primary_key and django_field.db_index:
                self._db_indexes.append(str(django_field.name))

            if not django_field.primary_key and django_field.unique:
                self._unique_constraints.append(str(django_field.name))

        self._fields.sort(key=lambda x: x.foreign_key, reverse=True)
        self._fields.sort(key=lambda x: x.primary_key, reverse=True)

        for composite_index_fields in meta.index_together:
            self._db_indexes.append(','.join(composite_index_fields))

        for unique_constraint_fields in meta.unique_together:
            self._unique_constraints.append(','.join(unique_constraint_fields))

    @property
    def markdown(self):
        """
        return field, index and unique constraint description of table in markdown string format

        Example output:

        ## water_mark_change_history_tab
        銀行帳戶水位變更歷程

        #### schema
        | field_name | type | description |
        |---|---|---|
        | id | PK, BIGINT AUTO_INCREMENT |  |
        | bank_account | FK, BIGINT |  |
        | water_mark | NUMERIC(18, 2) | 自有資金水位 |
        | create_time | DATE | 資料生效日期 |
        | expire_time | DATE | 資料截止日期 |


        #### additional info
        | type | value | description |
        |---|---|---|
        | index | bank_account | |

        """
        markdown_str = (
            f'## {self._meta.db_table}\n'
            f'{self._model_description}\n\n'
            f'#### schema\n'
            f'| field_name | type | description |\n|---|---|---|\n'
        )
        for field in self._fields:
            markdown_str += field.markdown_repr

        markdown_str += (
            f'\n\n'
            f'#### additional info\n'
            f'| type | value | description |\n|---|---|---|\n'
        )
        for index in self._db_indexes:
            markdown_str += (
                f'| index | {index.replace(",", ", ")} | |\n'
            )

        for unique_constraint in self._unique_constraints:
            markdown_str += (
                f'| unique | {unique_constraint.replace(",", ", ")} | |\n'
            )

        return markdown_str

    @property
    def plantuml_entity(self):
        """
        return plantuml format's entity string

        Example output:

        entity water_mark_change_history_tab {
            id: PK, BIGINT AUTO_INCREMENT
            bank_account: FK, BIGINT
            --
            water_mark: NUMERIC(18, 2)
            create_time: DATE
            expire_time: DATE
        }

        """
        plantuml_entity_str = f'entity {self._meta.db_table} {{\n'
        last_primary_or_foreign_key_index = None

        # get latest primary or foreign key index
        for i, f in enumerate(self._fields):
            if f.primary_key or f.foreign_key:
                last_primary_or_foreign_key_index = i

        for i, field in enumerate(self._fields):
            plantuml_entity_str += field.plantuml_entity_repr

            # add separator line between foreign/primary key and other field
            if i is not None and i == last_primary_or_foreign_key_index:
                plantuml_entity_str += '\t--\n'

        plantuml_entity_str += '}\n'
        return plantuml_entity_str


if __name__ == '__main__':
    from models import *

    for m in [Wallet, User, Merchant]:
        descriptor = ModelDescriptor(model=m)
        print(descriptor.markdown)
        print(descriptor.plantuml_entity)
