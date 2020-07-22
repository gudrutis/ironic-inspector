# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Added 'conditions_join_type' and 'invert_conditions_outcome' fields to
'rules' table.

Revision ID: 4c9b9b4712d6
Revises: b55109d5063a
Create Date: 2020-06-17 15:41:42.233295

"""
from alembic import op
import sqlalchemy as sa

from ironic_inspector.enums import RuleConditionJoinEnum as JoinEnum

# revision identifiers, used by Alembic.
revision = '4c9b9b4712d6'
down_revision = 'b55109d5063a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('rules', sa.Column('conditions_join_type',
                                     sa.Enum(*JoinEnum.all()),
                                     nullable=True, default=JoinEnum.AND,
                                     server_default=JoinEnum.AND))
    op.add_column('rules', sa.Column('invert_conditions_outcome', sa.Boolean,
                                     default=False,
                                     server_default="0"))
