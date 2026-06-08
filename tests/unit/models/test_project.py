import pytest
from datetime import datetime
from models.project import Project
from models.enums import ProjectStatus


@pytest.fixture
def valid_project() -> Project:
    return Project(
        id="p1",
        title="AI Research",
        description="Deep learning project",
        created_at=datetime(2025, 9, 1),
    )


class TestProjectCreation:
    def test_all_fields_set(self, valid_project):
        assert valid_project.id == "p1"
        assert valid_project.title == "AI Research"
        assert valid_project.description == "Deep learning project"
        assert valid_project.created_at == datetime(2025, 9, 1)

    def test_default_status_draft(self, valid_project):
        assert valid_project.status == ProjectStatus.DRAFT

    def test_default_team_id_none(self, valid_project):
        assert valid_project.team_id is None

    def test_explicit_status_active(self):
        p = Project("p2", "Web App", "desc", status=ProjectStatus.ACTIVE,
                    created_at=datetime(2025, 9, 1))
        assert p.status == ProjectStatus.ACTIVE

    def test_explicit_status_completed(self):
        p = Project("p3", "ML Model", "desc", status=ProjectStatus.COMPLETED,
                    created_at=datetime(2025, 9, 1))
        assert p.status == ProjectStatus.COMPLETED

    def test_explicit_status_archived(self):
        p = Project("p4", "Old Project", "desc", status=ProjectStatus.ARCHIVED,
                    created_at=datetime(2025, 9, 1))
        assert p.status == ProjectStatus.ARCHIVED

    def test_explicit_team_id(self):
        p = Project("p5", "Team Work", "desc", team_id="t1",
                    created_at=datetime(2025, 9, 1))
        assert p.team_id == "t1"

    def test_description_can_be_empty_string(self):
        p = Project("p6", "Title", "", created_at=datetime(2025, 9, 1))
        assert p.description == ""


class TestProjectIdValidation:
    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Project("", "Title", "desc", created_at=datetime(2025, 9, 1))

    def test_whitespace_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            Project("   ", "Title", "desc", created_at=datetime(2025, 9, 1))


class TestProjectDefaultCreatedAt:
    def test_created_at_set_automatically_when_not_provided(self):
        p = Project("p1", "Title", "desc")
        assert p.created_at is not None
        assert isinstance(p.created_at, datetime)


class TestProjectTitleValidation:
    def test_empty_title_raises(self):
        with pytest.raises(ValueError, match="title"):
            Project("p1", "", "desc", created_at=datetime(2025, 9, 1))

    def test_whitespace_title_raises(self):
        with pytest.raises(ValueError, match="title"):
            Project("p1", "   ", "desc", created_at=datetime(2025, 9, 1))
