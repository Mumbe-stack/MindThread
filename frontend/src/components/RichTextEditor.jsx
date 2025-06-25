import React from "react";
import { RichTextEditor } from "@mantine/rte";

const Editor = ({ value, onChange }) => {
  return (
    <div className="bg-white border rounded shadow-sm p-2">
      <RichTextEditor
        value={value}
        onChange={onChange}
        placeholder="Write your post content here..."
        controls={[
          ["bold", "italic", "underline", "strike", "clean"],
          ["unorderedList", "orderedList"],
          ["h1", "h2", "h3"],
          ["alignLeft", "alignCenter", "alignRight"],
          ["link", "image"],
        ]}
        className="min-h-[200px]"
      />
    </div>
  );
};

export default Editor;
