const TagList = ({ tags = [], onClick }) => {
  return (
    <div className="flex flex-wrap gap-2 my-2">
      {tags.map((tag, i) => (
        <span
          key={i}
          className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm cursor-pointer hover:bg-blue-200"
          onClick={() => onClick && onClick(tag)}
        >
          #{tag}
        </span>
      ))}
    </div>
  );
};

export default TagList;
