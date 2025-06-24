const ExportCSV = ({ data, filename }) => {
  const handleExport = () => {
    const csv = [
      Object.keys(data[0] || {}).join(","),
      ...data.map((row) =>
        Object.values(row).map((v) => `"${v}"`).join(",")
      ),
    ].join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    link.click();
  };

  return (
    <button onClick={handleExport} className="bg-green-600 text-white px-4 py-2 rounded shadow hover:bg-green-700">
      📥 Export CSV
    </button>
  );
};

export default ExportCSV;
