from pydantic import BaseModel, Field

class Todo(BaseModel):
    title: str = Field(min_length=1)
    done: bool = False

    def mark_done(self) -> None:
        self.done = True
        
